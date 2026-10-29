"""How good is a mind map? Reference-free metrics, comparable across methods.

There is no gold mind map for an arbitrary PDF, so every metric compares a map
to its source document using one shared embedder (MiniLM):

* coverage:      share of the document's passages that some node is about
                 (cosine >= COVER_AT). A node is scored on what a reader sees at a
                 glance: its label plus up to two keyword chips, capped at
                 GLANCE_WORDS words, so sentence-length labels can't buy coverage.
* grounded:      share of labels whose content words all occur in the document;
                 a cheap hallucination proxy (paraphrase is penalised too, so
                 read it alongside coverage).
* distinct:      1 - mean cosine between sibling labels; siblings that say the
                 same thing waste the reader's attention.
* heading recall: share of the headings found by the parser that the map has a
                 matching node for. Biased towards AutoMap, which builds on those
                 headings, so it is reported but not used to rank.

Baselines:
* naive:  the original AutoMap clustering mode: sentences -> HDBSCAN, labels are
          the first six words of a cluster's first sentence.
* flat:   AutoMap with the document structure ignored (clustering only) - an
          ablation showing what the headings contribute.
* llm:    one Gemini call returning the whole map (the original main mode).
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path

import numpy as np
from sklearn.cluster import HDBSCAN

from .embed import get_embedder
from .mindmap import MIN_PASSAGES_TO_CLUSTER, MindMap, Node, _Builder, build_mindmap, find_links
from .pdf import read_pdf
from .structure import build_sections
from .topics import STOP_WORDS

COVER_AT = 0.35
GLANCE_WORDS = 8
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]+")


def _labels(node: dict) -> list[dict]:
    return [node] + [d for c in node.get("children", []) for d in _labels(c)]


def _siblings(node: dict):
    kids = node.get("children", [])
    if len(kids) > 1:
        yield [k["label"] for k in kids]
    for k in kids:
        yield from _siblings(k)


def _depth(node: dict) -> int:
    return 1 + max((_depth(c) for c in node.get("children", [])), default=0)


def score_map(data: dict, passages: list[str], headings: list[str], doc_text: str, embedder) -> dict:
    nodes = [n for n in _labels(data["root"])[1:] if n["label"]]
    labels = [n["label"] for n in nodes]
    if not labels:
        return {"nodes": 0}
    glance = [" ".join(" ".join([n["label"], *n.get("keywords", [])[:2]]).split()[:GLANCE_WORDS]) for n in nodes]
    lab = embedder.encode(glance)
    pas = embedder.encode(passages)
    best = (pas @ lab.T).max(axis=1)

    vocab = set(w.lower() for w in _WORD.findall(doc_text))
    stop = set(STOP_WORDS)

    def grounded(label: str) -> bool:
        words = [w.lower() for w in _WORD.findall(label) if w.lower() not in stop]
        return all(w in vocab for w in words)

    sims = []
    for group in _siblings(data["root"]):
        v = embedder.encode(group)
        s = v @ v.T
        sims.extend(s[np.triu_indices(len(group), 1)])

    recall = None
    if headings:
        h = embedder.encode(headings)
        recall = float(((h @ embedder.encode(labels).T).max(axis=1) >= 0.7).mean())

    return {
        "nodes": len(labels),
        "depth": _depth(data["root"]) - 1,
        "coverage": float((best >= COVER_AT).mean()),
        "grounded": float(np.mean([grounded(l) for l in labels])),
        "distinct": float(1 - np.mean(sims)) if sims else None,
        "heading_recall": recall,
        "label_words": float(np.mean([len(l.split()) for l in labels])),
    }


def naive_map(pdf: Path, embedder) -> dict:
    """Re-implementation of the original AutoMap 'Discovery' mode (minus UMAP)."""
    with __import__("pymupdf").open(pdf) as doc:
        text = "".join(p.get_text() for p in doc)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if 20 < len(s.strip()) < 500]
    ids = itertools.count()
    root = {"id": "x", "label": pdf.stem, "kind": "document", "children": []}
    if len(sentences) < 5:
        return {"root": root}
    vecs = embedder.encode(sentences)
    labels = HDBSCAN(min_cluster_size=3, min_samples=1, cluster_selection_method="leaf").fit_predict(vecs)
    for c in sorted(set(labels) - {-1}):
        members = [sentences[i] for i in np.flatnonzero(labels == c)]
        head = " ".join(members[0].split()[:6])
        root["children"].append({
            "id": f"x{next(ids)}", "label": f"Topic {c}: {head}", "kind": "topic",
            # the original cut at 70 characters; cut at a word boundary so grounding isn't
            # penalised for half-words
            "children": [{"id": f"x{next(ids)}", "label": m[:70].rsplit(" ", 1)[0], "kind": "topic"} for m in members[:4]],
        })
    return {"root": root}


def flat_map(pdf: Path, embedder) -> dict:
    """AutoMap with headings ignored: clustering alone has to find the structure."""
    doc = read_pdf(pdf)
    passages = build_sections(doc).all_passages
    vecs = embedder.encode([p.text for p in passages])
    b = _Builder(passages, vecs, embedder)
    root = Node(b.new_id(), doc.title, "document")
    idx = list(range(len(passages)))
    root.children = b.topics(idx, doc.title, max_k=6) if len(idx) >= MIN_PASSAGES_TO_CLUSTER else []
    return MindMap(doc.title, root, passages, find_links(root, b), {}).to_dict()


def _fmt(v) -> str:
    if v is None:
        return "–"
    return f"{v:.2f}" if isinstance(v, float) else str(v)


def run_eval(pdfs: list[Path], include_llm: bool = False) -> str:
    embedder = get_embedder("minilm")
    methods = ["automap", "flat", "naive"] + (["llm"] if include_llm else [])
    cols = ["nodes", "depth", "coverage", "grounded", "distinct", "heading_recall", "label_words"]
    rows, totals = [], {m: {c: [] for c in cols} for m in methods}
    for pdf in pdfs:
        doc = read_pdf(pdf)
        passages = [p.text for p in build_sections(doc).all_passages]
        headings = [h.text for h in doc.headings]
        doc_text = " ".join(b.text for b in doc.blocks)
        for m in methods:
            try:
                if m == "automap":
                    data = build_mindmap(pdf, embedder).to_dict()
                elif m == "flat":
                    data = flat_map(pdf, embedder)
                elif m == "naive":
                    data = naive_map(pdf, embedder)
                else:
                    from .llm import llm_mindmap

                    data = llm_mindmap(pdf)
            except Exception as e:  # one failing method shouldn't sink the report
                rows.append(f"| {pdf.stem[:28]} | {m} | failed: {e} |")
                continue
            s = score_map(data, passages, headings, doc_text, embedder)
            rows.append(f"| {pdf.stem[:28]} | {m} | " + " | ".join(_fmt(s.get(c)) for c in cols) + " |")
            for c in cols:
                if s.get(c) is not None:
                    totals[m][c].append(s[c])

    head = "| document | method | " + " | ".join(cols) + " |\n|" + "---|" * (len(cols) + 2)
    summary = [
        f"| **mean** | **{m}** | " + " | ".join(_fmt(float(np.mean(v))) if v else "–" for v in totals[m].values()) + " |"
        for m in methods
    ]
    return "\n".join([head, *rows, *summary])
