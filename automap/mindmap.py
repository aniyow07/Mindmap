"""PDF -> mind map. The document's own headings form the skeleton; embedding
clusters fill in topics where a section is long; similarity links connect
related ideas that live in different branches."""

from __future__ import annotations

import itertools
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

from .embed import Embedder, TfidfEmbedder, get_embedder
from .pdf import read_pdf
from .structure import Passage, Section, build_sections, short_label
from .topics import STOP_WORDS, _TOKEN, central_sentence, cluster, label_groups

MIN_PASSAGES_TO_CLUSTER = 6
MAX_LINKS_PER_NODE = 2


@dataclass
class Node:
    id: str
    label: str
    kind: str  # document | section | topic
    title: str = ""
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    passages: list[int] = field(default_factory=list)  # indices into MindMap.passages, this node only
    children: list["Node"] = field(default_factory=list)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def subtree_passages(self) -> list[int]:
        return [i for n in self.walk() for i in n.passages]


@dataclass
class Link:
    source: str
    target: str
    score: float
    shared: list[str]


@dataclass
class MindMap:
    title: str
    root: Node
    passages: list[Passage]
    links: list[Link]
    stats: dict

    def to_dict(self) -> dict:
        def node(n: Node) -> dict:
            d = {"id": n.id, "label": n.label, "kind": n.kind}
            if n.title and n.title != n.label:
                d["title"] = n.title
            if n.summary:
                d["summary"] = n.summary
            if n.keywords:
                d["keywords"] = n.keywords
            if n.passages:
                d["passages"] = n.passages
            if n.children:
                d["children"] = [node(c) for c in n.children]
            return d

        return {
            "title": self.title,
            "root": node(self.root),
            "passages": [{"text": p.text, "page": p.page} for p in self.passages],
            "links": [{"source": l.source, "target": l.target, "score": round(l.score, 3), "shared": l.shared} for l in self.links],
            "stats": self.stats,
        }


class _Builder:
    def __init__(self, passages: list[Passage], vecs: np.ndarray, embedder: Embedder):
        self.passages = passages
        self.texts = [p.text for p in passages]
        self.vecs = vecs
        self.embedder = embedder
        self.index = {id(p): i for i, p in enumerate(passages)}
        self.counter = itertools.count()
        self.silhouettes: list[float] = []

    def new_id(self) -> str:
        return f"n{next(self.counter)}"

    def centroid(self, idx: list[int]) -> np.ndarray:
        c = self.vecs[idx].mean(axis=0)
        return c / (np.linalg.norm(c) or 1)

    def summary(self, idx: list[int]) -> str:
        if not idx:
            return ""
        c = self.centroid(idx)
        best = idx[int(np.argmax(self.vecs[idx] @ c))]
        return central_sentence(self.texts[best], c, self.embedder)

    def topics(self, idx: list[int], parent_label: str, max_k: int = 6, depth: int = 0) -> list[Node]:
        from .topics import choose_k

        _, score = choose_k(self.vecs[idx], max_k)
        self.silhouettes.append(score)
        found = cluster([self.texts[i] for i in idx], self.vecs[idx], self.embedder, max_k)
        nodes = []
        for t in found:
            members = [idx[m] for m in t.members]
            label = t.label
            if label.lower() == parent_label.lower() and len(t.keywords) > 1:
                label = t.keywords[1].title()
            node = Node(self.new_id(), label, "topic", keywords=t.keywords, summary=self.summary(members))
            # Without headings to lean on, split big topics once more.
            if depth == 0 and max_k > 4 and len(members) >= 2 * MIN_PASSAGES_TO_CLUSTER:
                node.children = self.topics(members, label, max_k=4, depth=1)
            else:
                node.passages = members
            nodes.append(node)
        return nodes

    def section(self, s: Section, kind: str = "section") -> Node:
        node = Node(self.new_id(), short_label(s.title), kind, title=s.title)
        own = [self.index[id(p)] for p in s.passages]
        children = [self.section(c) for c in s.children]
        if len(own) >= MIN_PASSAGES_TO_CLUSTER and (not children or len(own) >= 2 * MIN_PASSAGES_TO_CLUSTER):
            max_k = 6 if not children else 4
            node.children = self.topics(own, node.label, max_k=max_k) + children
        else:
            node.passages = own
            node.children = children
        node.summary = self.summary(node.subtree_passages())
        self.name_sections(node)
        return node

    def name_sections(self, node: Node) -> None:
        """Keywords for sibling sections, contrasted against each other (c-TF-IDF)."""
        sections = [c for c in node.children if c.kind == "section" and c.subtree_passages()]
        if len(sections) < 2:
            return
        groups = [c.subtree_passages() for c in sections]
        for c, (_, keywords) in zip(sections, label_groups(self.texts, groups, self.vecs, self.embedder)):
            c.keywords = keywords


def _shared_terms(a: str, b: str, k: int = 3) -> list[str]:
    vec = CountVectorizer(ngram_range=(1, 2), stop_words=STOP_WORDS, token_pattern=_TOKEN)
    try:
        counts = vec.fit_transform([a, b]).toarray()
    except ValueError:
        return []
    both = np.minimum(counts[0], counts[1]) * (1 + np.char.count(vec.get_feature_names_out().astype(str), " "))
    terms = vec.get_feature_names_out()
    return [terms[i] for i in np.argsort(-both)[:k] if both[i] > 0]


def find_links(root: Node, builder: _Builder) -> list[Link]:
    """Cross-links between nodes in different branches whose content is unusually similar.

    'Unusually' is relative: a pair must beat the mean pairwise similarity by
    1.5 standard deviations, so the threshold adapts to the embedder and document.
    """
    parent: dict[str, str | None] = {root.id: None}
    for n in root.walk():
        for c in n.children:
            parent[c.id] = n.id

    def ancestors(node_id: str) -> set[str]:
        out = set()
        while node_id is not None:
            out.add(node_id)
            node_id = parent[node_id]
        return out

    # Only nodes that hold text directly: linking a whole chapter to a topic elsewhere says little.
    nodes = [n for n in root.walk() if n is not root and n.passages]
    if len(nodes) < 3:
        return []
    cents = np.stack([builder.centroid(n.subtree_passages()) for n in nodes])
    sims = cents @ cents.T
    anc = {n.id: ancestors(n.id) for n in nodes}
    pairs = []
    for i, j in itertools.combinations(range(len(nodes)), 2):
        a, b = nodes[i], nodes[j]
        if a.id in anc[b.id] or b.id in anc[a.id] or parent[a.id] == parent[b.id]:
            continue
        pairs.append((sims[i, j], i, j))
    if not pairs:
        return []
    scores = np.array([p[0] for p in pairs])
    threshold = max(scores.mean() + 1.5 * scores.std(), 0.2)
    degree: dict[str, int] = {}
    links = []
    budget = max(3, len(nodes) // 3)
    for score, i, j in sorted(pairs, reverse=True):
        if score < threshold or len(links) >= budget:
            break
        a, b = nodes[i], nodes[j]
        if degree.get(a.id, 0) >= MAX_LINKS_PER_NODE or degree.get(b.id, 0) >= MAX_LINKS_PER_NODE:
            continue
        text_a = " ".join(builder.texts[k] for k in a.subtree_passages())
        text_b = " ".join(builder.texts[k] for k in b.subtree_passages())
        links.append(Link(a.id, b.id, float(score), _shared_terms(text_a, text_b)))
        degree[a.id] = degree.get(a.id, 0) + 1
        degree[b.id] = degree.get(b.id, 0) + 1
    return links


def build_mindmap(path: str | Path, embedder: Embedder | str | None = None) -> MindMap:
    started = time.perf_counter()
    doc = read_pdf(path)
    sections = build_sections(doc)
    passages = sections.all_passages
    if not passages:
        raise ValueError("No readable text found. Is this a scanned PDF? (OCR isn't supported yet.)")
    if embedder is None:
        embedder = os.getenv("AUTOMAP_EMBEDDER", "auto")
    if isinstance(embedder, str):
        embedder = get_embedder(embedder)
    if isinstance(embedder, TfidfEmbedder):
        embedder.fit([p.text for p in passages])
    vecs = embedder.encode([p.text for p in passages])

    builder = _Builder(passages, vecs, embedder)
    root = builder.section(sections, kind="document")
    root.label = doc.title
    links = find_links(root, builder)

    nodes = list(root.walk())
    stats = {
        "pages": doc.page_count,
        "passages": len(passages),
        "headings_detected": len(doc.headings),
        "running_lines_removed": len(doc.removed),
        "sections": sum(n.kind == "section" for n in nodes),
        "topics": sum(n.kind == "topic" for n in nodes),
        "links": len(links),
        "mean_silhouette": round(float(np.mean(builder.silhouettes)), 3) if builder.silhouettes else None,
        "embedder": embedder.name,
        "seconds": round(time.perf_counter() - started, 2),
    }
    return MindMap(doc.title, root, passages, links, stats)
