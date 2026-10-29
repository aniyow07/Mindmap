import numpy as np
import pytest

from automap.embed import TfidfEmbedder
from automap.evaluate import score_map
from automap.llm import _to_mindmap
from automap.mindmap import build_mindmap
from automap.pdf import read_pdf
from automap.structure import build_sections, short_label
from automap.topics import choose_k, label_groups

from conftest import FINANCE, VISION


# ---- pdf ----

def test_title_and_running_text(paper):
    doc = read_pdf(paper)
    assert doc.title == "A Tale of Two Topics"
    assert "Journal of Synthetic Tests" in doc.removed
    assert not any("Journal of Synthetic" in b.text for b in doc.blocks)
    assert not any(b.text.strip() in {"1", "2", "3"} for b in doc.blocks)


def test_heading_levels(paper):
    levels = {h.text: h.level for h in read_pdf(paper).headings}
    assert levels["1. Image models"] == 1
    assert levels["2. Hedging"] == 1
    assert levels["2.1 Dynamic hedge"] == 2
    assert "Ada Author, University of Testing" not in levels


# ---- structure ----

def test_sections_nest_and_skip_references(paper):
    root = build_sections(read_pdf(paper))
    titles = [s.title for s in root.children]
    assert titles == ["Abstract", "1. Image models", "2. Hedging"]
    hedging = root.children[2]
    assert [c.title for c in hedging.children] == ["2.1 Dynamic hedge"]
    assert all("cited work" not in p.text for p in root.all_passages)


@pytest.mark.parametrize(
    "title, label",
    [
        ("3. Deep Q-Learning: Theoretical Foundations", "Deep Q-Learning: Theoretical Foundations"),
        ("1. “HGC: Fast Hierarchical Clustering for Large-Scale Single-Cell Data” (Bioinformatics, 2021)", "HGC"),
        ("Results", "Results"),
    ],
)
def test_short_label(title, label):
    assert short_label(title) == label


# ---- topics ----

def _two_topic_corpus():
    vision = [f"{VISION} Variant {i}." for i in range(5)]
    finance = [f"{FINANCE} Variant {i}." for i in range(5)]
    texts = vision + finance
    emb = TfidfEmbedder().fit(texts)
    return texts, emb.encode(texts), emb


def test_choose_k_separates_obvious_topics():
    texts, vecs, _ = _two_topic_corpus()
    labels, score = choose_k(vecs, max_k=4)
    assert len(set(labels[:5])) == 1 and len(set(labels[5:])) == 1
    assert labels[0] != labels[5]
    assert score > 0.5


def test_labels_are_distinctive():
    texts, vecs, emb = _two_topic_corpus()
    (vision_label, vision_kw), (finance_label, finance_kw) = label_groups(texts, [list(range(5)), list(range(5, 10))], vecs, emb)
    assert any(w in " ".join(vision_kw).lower() for w in ("convolution", "image", "filters"))
    assert any(w in " ".join(finance_kw).lower() for w in ("hedge", "hedging", "option"))
    assert vision_label != finance_label


# ---- end to end ----

def test_build_mindmap_is_consistent(paper):
    data = build_mindmap(paper, embedder=TfidfEmbedder()).to_dict()
    assert data["title"] == "A Tale of Two Topics"
    n_passages = len(data["passages"])
    ids, parent = set(), {}

    def walk(node, up=None):
        ids.add(node["id"])
        parent[node["id"]] = up
        for i in node.get("passages", []):
            assert 0 <= i < n_passages
        for c in node.get("children", []):
            walk(c, node["id"])

    walk(data["root"])
    for link in data["links"]:
        assert link["source"] in ids and link["target"] in ids
        assert parent[link["source"]] != link["target"] and parent[link["target"]] != link["source"]
    assert data["stats"]["headings_detected"] == 5


def test_rejects_textless_pdf(tmp_path):
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    path = tmp_path / "blank.pdf"
    doc.save(path)
    with pytest.raises(ValueError, match="No readable text"):
        build_mindmap(path, embedder=TfidfEmbedder())


# ---- llm baseline + evaluation ----

def test_llm_output_converts_to_mindmap():
    raw = {"title": "Doc", "children": [{"label": "A", "children": [{"label": "A1"}]}, {"label": "B"}]}
    data = _to_mindmap(raw)
    assert data["root"]["label"] == "Doc"
    assert [c["label"] for c in data["root"]["children"]] == ["A", "B"]
    assert data["root"]["children"][0]["children"][0]["label"] == "A1"


def test_score_map_rewards_grounded_distinct_labels():
    passages = [VISION, FINANCE]
    emb = TfidfEmbedder().fit(passages + ["convolution image filters", "option hedge ratio", "unicorn galaxy"])
    good = {"root": {"label": "doc", "children": [{"label": "convolution image filters"}, {"label": "option hedge ratio"}]}}
    bad = {"root": {"label": "doc", "children": [{"label": "unicorn galaxy"}, {"label": "unicorn galaxy"}]}}
    s_good = score_map(good, passages, [], VISION + FINANCE, emb)
    s_bad = score_map(bad, passages, [], VISION + FINANCE, emb)
    assert s_good["grounded"] == 1.0 and s_bad["grounded"] == 0.0
    assert s_good["distinct"] > s_bad["distinct"]
    assert s_good["coverage"] > s_bad["coverage"]
