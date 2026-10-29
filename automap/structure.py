"""Turn a parsed document into a section tree with passages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .pdf import Block, Document

PASSAGE_WORDS = 90  # target passage length; long enough to embed well, short enough to quote
MIN_PASSAGE_WORDS = 12
_SKIP_SECTIONS = re.compile(r"^(\d+\.?\s*)?(references|bibliography|works cited|publications/references|acknowledg\w*)\b", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"“])")
_BOILERPLATE = re.compile(
    r"(\S+@\S+\.\w+|creative commons|open access|licen[cs]e|copyright|©|received:|accepted:|published online|"
    r"correspondence|doi\.org|https?://|www\.|university|department|faculty|institute)",
    re.I,
)
_LEADING_NUMBER = re.compile(r"^(\d+(\.\d+)*|[IVXLC]+)[.)]?\s+")


@dataclass
class Passage:
    text: str
    page: int


@dataclass
class Section:
    title: str
    level: int
    page: int
    passages: list[Passage] = field(default_factory=list)
    children: list["Section"] = field(default_factory=list)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    @property
    def all_passages(self) -> list[Passage]:
        return [p for s in self.walk() for p in s.passages]


def short_label(title: str, max_words: int = 7) -> str:
    """'3. “HGC: Fast Hierarchical Clustering…” (Bioinformatics, 2021)' -> 'HGC'."""
    t = _LEADING_NUMBER.sub("", title).strip().strip("“”\"'")
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)  # trailing (Venue, Year)
    t = t.rstrip(":").strip("“”\"' ")
    if len(t.split()) > max_words and ":" in t:
        t = t.split(":")[0]
    words = t.split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")


def _is_boilerplate(text: str) -> bool:
    """Affiliations, licences, journal furniture: two or more cues in one short passage."""
    cues = len(_BOILERPLATE.findall(text))
    return cues >= 2 and cues * 25 >= len(text.split())


def _split_passages(blocks: list[Block]) -> list[Passage]:
    """Pack sentences into ~PASSAGE_WORDS chunks, never crossing a page boundary."""
    passages: list[Passage] = []
    buf: list[str] = []
    page = blocks[0].page if blocks else 1

    def flush():
        text = " ".join(buf).strip()
        if _is_boilerplate(text):
            buf.clear()
            return
        if len(text.split()) >= MIN_PASSAGE_WORDS:
            passages.append(Passage(text, page))
        elif text and passages and passages[-1].page == page:
            passages[-1].text += " " + text
        buf.clear()

    for b in blocks:
        if b.page != page:
            flush()
            page = b.page
        for sentence in _SENTENCE.split(b.text):
            buf.append(sentence)
            if sum(len(s.split()) for s in buf) >= PASSAGE_WORDS:
                flush()
    flush()
    return passages


def build_sections(doc: Document) -> Section:
    root = Section(doc.title, 0, 1)
    stack = [root]
    pending: list[Block] = []
    skipping = False

    def attach_pending():
        if pending and not skipping:
            stack[-1].passages.extend(_split_passages(pending))
        pending.clear()

    for b in doc.blocks:
        if not b.is_heading:
            pending.append(b)
            continue
        attach_pending()
        skipping = bool(_SKIP_SECTIONS.match(b.text))
        if skipping:
            continue
        while stack[-1].level >= b.level:
            stack.pop()
        node = Section(b.text, b.level, b.page)
        stack[-1].children.append(node)
        stack.append(node)
    attach_pending()
    _prune(root)
    return root


def _prune(section: Section) -> None:
    """Drop headings with nothing under them (stray bold lines, empty stubs)."""
    for c in section.children:
        _prune(c)
    section.children = [c for c in section.children if c.passages or c.children]
