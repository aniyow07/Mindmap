"""Clustering passages into topics and naming them.

Clustering: agglomerative (average linkage, cosine) over passage embeddings,
with the number of topics picked by silhouette score. On the few dozen passages
a section has, this is more stable than density-based methods like HDBSCAN,
which tend to label most of a small sample as noise.

Labelling is two-stage, in the spirit of BERTopic + KeyBERT:
1. class-based TF-IDF proposes candidate phrases that are frequent in this
   cluster but rare in its sibling clusters;
2. the candidates are re-ranked by embedding similarity to the cluster centroid,
   with maximal marginal relevance so the keywords aren't near-duplicates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from sklearn.metrics import silhouette_score

from .embed import Embedder

MAX_TOPICS = 6
_EXTRA_STOP = {
    "et", "al", "fig", "figure", "table", "section", "paper", "study", "studies", "result", "results",
    "use", "used", "using", "based", "approach", "proposed", "method", "methods", "also", "however",
    "shown", "show", "shows", "given", "case", "eq", "equation", "work", "new", "different",
    "high", "low", "provide", "provides", "present", "presents", "include", "including", "s",
}
STOP_WORDS = list(ENGLISH_STOP_WORDS | _EXTRA_STOP)
_TOKEN = r"(?u)\b[A-Za-z][A-Za-z0-9\-]{1,}\b"


@dataclass
class Topic:
    members: list[int]  # indices into the passages given to cluster()
    label: str
    keywords: list[str]
    central: int  # index of the passage closest to the centroid


def choose_k(x: np.ndarray, max_k: int = MAX_TOPICS) -> tuple[np.ndarray, float]:
    """Cluster with the k in [2, max_k] that maximises the cosine silhouette."""
    n = len(x)
    if n < 4:
        return np.zeros(n, dtype=int), 0.0
    best = (np.zeros(n, dtype=int), -1.0)
    for k in range(2, min(max_k, n // 2) + 1):
        labels = AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average").fit_predict(x)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(x, labels, metric="cosine")
        # tiny clusters make silhouette look good without helping a reader
        if min(np.bincount(labels)) < 2:
            score -= 0.05
        if score > best[1]:
            best = (labels, score)
    return best


def _candidates(docs: list[str], top_n: int = 12) -> list[list[str]]:
    """c-TF-IDF: each cluster's text is one 'class document'."""
    vec = CountVectorizer(ngram_range=(1, 2), stop_words=STOP_WORDS, token_pattern=_TOKEN, lowercase=True)
    try:
        counts = vec.fit_transform(docs).toarray().astype(float)
    except ValueError:  # all stop words
        return [[] for _ in docs]
    terms = vec.get_feature_names_out()
    tf = counts / np.maximum(counts.sum(axis=1, keepdims=True), 1)
    avg_words = counts.sum() / len(docs)
    idf = np.log(1 + avg_words / np.maximum(counts.sum(axis=0), 1))
    ctfidf = tf * idf
    # prefer phrases: a bigram that appears is more informative than its parts
    ngram_len = np.array([t.count(" ") + 1 for t in terms])
    ctfidf *= 1 + 0.25 * (ngram_len - 1)
    # A phrase that occurs once is usually an accident of wording (or an author's
    # affiliation), not what the cluster is about.
    ctfidf[(counts < 2) & (counts.sum(axis=1, keepdims=True) > 150)] = 0
    return [[terms[i] for i in np.argsort(-row)[:top_n] if row[i] > 0] for row in ctfidf]


def _mmr(centroid: np.ndarray, cand_vecs: np.ndarray, k: int, diversity: float = 0.5) -> list[int]:
    relevance = cand_vecs @ centroid
    chosen = [int(np.argmax(relevance))]
    while len(chosen) < min(k, len(cand_vecs)):
        redundancy = (cand_vecs @ cand_vecs[chosen].T).max(axis=1)
        score = (1 - diversity) * relevance - diversity * redundancy
        score[chosen] = -np.inf
        chosen.append(int(np.argmax(score)))
    return chosen


def _pretty(phrase: str) -> str:
    words = phrase.split()
    return " ".join(w if (w.isupper() or any(c.isdigit() for c in w)) else w.capitalize() for w in words)


def label_groups(texts: list[str], groups: list[list[int]], vecs: np.ndarray, embedder: Embedder, n_keywords: int = 5) -> list[tuple[str, list[str]]]:
    """Name each group of texts. Groups are labelled against each other, so pass siblings together."""
    docs = [" ".join(texts[i] for i in g) for g in groups]
    out = []
    for g, cands in zip(groups, _candidates(docs)):
        if not cands:
            out.append(("Misc", []))
            continue
        # Restore original casing (keeps acronyms like CNN, HGC) from the source text.
        joined = " ".join(texts[i] for i in g)
        cased = []
        for c in cands:
            m = re.search(r"\b" + re.escape(c).replace(r"\ ", r"\s+") + r"\b", joined, re.I)
            cased.append(m.group(0) if m else c)
        centroid = vecs[g].mean(axis=0)
        centroid /= np.linalg.norm(centroid) or 1
        order = _mmr(centroid, embedder.encode(cased), n_keywords)
        keywords = [cased[i] for i in order]
        out.append((_pretty(keywords[0]), keywords))
    return out


def cluster(texts: list[str], vecs: np.ndarray, embedder: Embedder, max_k: int = MAX_TOPICS) -> list[Topic]:
    labels, _ = choose_k(vecs, max_k)
    groups = [list(np.flatnonzero(labels == c)) for c in sorted(set(labels))]
    named = label_groups(texts, groups, vecs, embedder)
    topics = []
    for g, (label, keywords) in zip(groups, named):
        centroid = vecs[g].mean(axis=0)
        central = g[int(np.argmax(vecs[g] @ centroid))]
        topics.append(Topic(g, label, keywords, central))
    return topics


def central_sentence(text: str, centroid: np.ndarray, embedder: Embedder, max_words: int = 40) -> str:
    """The sentence of a passage that best represents the centroid: an extractive one-line summary."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if 6 <= len(s.split()) <= 60] or [text]
    best = sentences[int(np.argmax(embedder.encode(sentences) @ centroid))]
    words = best.split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")
