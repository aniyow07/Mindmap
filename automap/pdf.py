"""Layout-aware PDF reading.

Plain `page.get_text()` flattens a PDF into one string and throws away the
signals that tell you how the document is organised. Here we keep each text
block with its font size, weight and position, then use those to:

* drop running headers/footers (text repeated in the page margins),
* find headings (larger or bold short blocks) and group their styles into levels,
* skip front matter (authors, affiliations) that precedes the abstract,
* fall back to the PDF's embedded outline when it is trustworthy.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

MARGIN_FRACTION = 0.08  # top/bottom band where running headers live
REPEAT_FRACTION = 0.4  # repeated on this share of pages => header/footer
MAX_HEADING_WORDS = 14  # bold body-size text
MAX_LARGE_HEADING_WORDS = 25  # visibly larger text can run longer (paper titles in a list)
SAME_TIER_RATIO = 1.06  # sizes this close are one heading level
MAX_LEVELS = 3

_NUMBERED = re.compile(r"^(\d+(\.\d+)*|[IVXLC]+|[A-Z])[.)]?\s+\S")
_FRONT_MATTER_END = re.compile(r"^(\d+\.?\s*)?(abstract|introduction|summary|overview)\b", re.I)
_PAGE_NUMBER = re.compile(r"^(page\s*)?\d+(\s*(of|/)\s*\d+)?$", re.I)


@dataclass
class Block:
    text: str
    page: int  # 1-based
    size: float
    bold: bool
    y0: float
    y1: float
    page_height: float
    level: int | None = None  # set for headings; 1 = top level

    @property
    def is_heading(self) -> bool:
        return self.level is not None

    @property
    def words(self) -> int:
        return len(self.text.split())

    @property
    def style(self) -> tuple[float, bool]:
        return (self.size, self.bold)


@dataclass
class Document:
    title: str
    blocks: list[Block]
    page_count: int
    body_size: float
    removed: list[str] = field(default_factory=list)  # header/footer lines dropped

    @property
    def headings(self) -> list[Block]:
        return [b for b in self.blocks if b.is_heading]


def _clean(text: str) -> str:
    text = text.replace("\xa0", " ").replace("­", "").replace("‑", "-")
    text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)  # re-join hyphenated line breaks
    return re.sub(r"\s+", " ", text).strip()


def _line_style(line: dict) -> tuple[float, bool] | None:
    """(size, bold) for a line: the size most of its characters use, and bold only
    when nearly the whole line is bold (a few bold words are inline emphasis)."""
    sizes, bold_chars, total = Counter(), 0, 0
    for s in line["spans"]:
        n = len(s["text"].strip())
        if n:
            sizes[round(s["size"], 1)] += n
            total += n
            bold_chars += n if s["flags"] & 16 else 0
    if not total:
        return None
    return sizes.most_common(1)[0][0], bold_chars >= 0.9 * total


def _read_blocks(pdf: pymupdf.Document) -> list[Block]:
    """Text blocks, with a leading heading split off from the paragraph under it.

    PyMuPDF often returns a heading and its paragraph as one block (posters and
    slides especially). Only a *leading* run of bigger or bolder lines is split
    off: style changes mid-paragraph are inline emphasis or maths fonts.
    """
    blocks = []
    for page in pdf:
        height = page.rect.height
        for raw in page.get_text("dict", sort=True)["blocks"]:
            lines = [(line, _line_style(line)) for line in raw.get("lines", [])]
            lines = [(line, style) for line, style in lines if style is not None]
            if not lines:
                continue
            body_style = _dominant([style for _, style in lines], [line for line, _ in lines])
            head = 0
            while head < len(lines) and lines[head][1] != body_style and _stronger(lines[head][1], body_style):
                head += 1
            parts = [lines[:head], lines[head:]] if 0 < head < len(lines) else [lines]
            for part in parts:
                size, bold = _dominant([style for _, style in part], [line for line, _ in part])
                text = _clean("\n".join("".join(s["text"] for s in line["spans"]) for line, _ in part))
                if text:
                    blocks.append(Block(text, page.number + 1, size, bold, part[0][0]["bbox"][1], part[-1][0]["bbox"][3], height))
    return blocks


def _dominant(styles: list[tuple[float, bool]], lines: list[dict]) -> tuple[float, bool]:
    weight = Counter()
    for style, line in zip(styles, lines):
        weight[style] += sum(len(s["text"].strip()) for s in line["spans"])
    return weight.most_common(1)[0][0]


def _stronger(style: tuple[float, bool], than: tuple[float, bool]) -> bool:
    return style[0] > than[0] * 1.05 or (style[1] and not than[1] and style[0] >= than[0] * 0.95)


def _margin_key(block: Block) -> str | None:
    top = block.y1 < block.page_height * MARGIN_FRACTION
    bottom = block.y0 > block.page_height * (1 - MARGIN_FRACTION)
    if not (top or bottom):
        return None
    return re.sub(r"\d+", "#", block.text.lower())


def _drop_running_text(blocks: list[Block], page_count: int) -> tuple[list[Block], list[str]]:
    """Remove page numbers and text that repeats in the margins across pages."""
    pages_with = Counter(key for key, _ in {(_margin_key(b), b.page) for b in blocks} if key)
    threshold = max(2, REPEAT_FRACTION * page_count)
    running = {k for k, n in pages_with.items() if n >= threshold}

    kept, removed = [], []
    for b in blocks:
        key = _margin_key(b)
        if key and (key in running or _PAGE_NUMBER.match(b.text)):
            removed.append(b.text)
        else:
            kept.append(b)
    return kept, sorted(set(removed))


def _body_size(blocks: list[Block]) -> float:
    by_size = Counter()
    for b in blocks:
        by_size[b.size] += len(b.text)
    return by_size.most_common(1)[0][0] if by_size else 10.0


def _find_title(pdf: pymupdf.Document, blocks: list[Block], body: float) -> tuple[str, float | None]:
    first = [b for b in blocks if b.page == 1 and b.words <= 30 and b.size > body * 1.2]
    if first:
        size = max(b.size for b in first)
        # long titles wrap into several blocks of the same size
        return " ".join(b.text for b in first if b.size == size), size
    meta = (pdf.metadata or {}).get("title", "").strip()
    if meta and not meta.lower().endswith((".pdf", ".pptx", ".docx")):
        return meta, None
    return "", None


def _looks_like_heading(b: Block, body: float) -> bool:
    bigger = b.size >= body * 1.15
    emphasised = b.bold and b.size >= body * 0.95
    limit = MAX_LARGE_HEADING_WORDS if bigger else MAX_HEADING_WORDS
    if b.words == 0 or b.words > limit:
        return False
    if not any(c.isalpha() for c in b.text):
        return False
    if b.text.endswith((".", ",", ";")) and not _NUMBERED.match(b.text):
        return False
    return bigger or emphasised


def _style_tiers(candidates: list[Block]) -> list[set[tuple[float, bool]]]:
    """Group heading styles into levels, biggest first.

    Sizes within ~6% of each other with the same weight are the same level:
    designers nudge sizes to make text fit (posters especially), and that should
    not create a new level of hierarchy.
    """
    styles = Counter(b.style for b in candidates)
    tiers: list[list[tuple[float, bool]]] = []
    for style in sorted(styles, key=lambda s: (-s[0], not s[1])):
        tier = next((t for t in tiers if t[0][1] == style[1] and t[-1][0] / style[0] <= SAME_TIER_RATIO), None)
        if tier is None:
            tiers.append([style])
        else:
            tier.append(style)
    # A tier used only once is usually decoration (a lone banner), so it only
    # counts when there are few tiers anyway.
    if len(tiers) > MAX_LEVELS:
        tiers = [t for t in tiers if sum(styles[s] for s in t) > 1] or tiers
    return [set(t) for t in tiers[:MAX_LEVELS]]


def _assign_levels(blocks: list[Block], body: float, title_size: float | None) -> None:
    candidates = [b for b in blocks if _looks_like_heading(b, body) and b.size != title_size]
    # Author lists, affiliations and report numbers before the abstract are not
    # sections. Drop them before ranking styles so they can't claim a level.
    start = next((i for i, b in enumerate(candidates) if b.page <= 3 and _FRONT_MATTER_END.match(b.text)), 0)
    candidates = candidates[start:]
    for level, tier in enumerate(_style_tiers(candidates), start=1):
        for b in candidates:
            if b.style in tier:
                b.level = level


def _merge_wrapped_headings(blocks: list[Block]) -> list[Block]:
    """A numbered heading that wraps onto the next page arrives as two blocks."""
    merged: list[Block] = []
    for b in blocks:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and prev.is_heading
            and b.is_heading
            and prev.style == b.style
            and _NUMBERED.match(prev.text)
            and not _NUMBERED.match(b.text)
        ):
            prev.text = f"{prev.text} {b.text}"
            continue
        merged.append(b)
    return merged


def _apply_outline(pdf: pymupdf.Document, blocks: list[Block]) -> bool:
    """Use the PDF's own bookmarks when they actually point at heading text."""
    toc = [(lvl, _clean(t), p) for lvl, t, p in pdf.get_toc() if t.strip()]
    if len(toc) < 4:
        return False
    matched = []
    for lvl, title, page in toc:
        key = title.lower()
        hit = next((i for i, b in enumerate(blocks) if b.page == page and b.text.lower().startswith(key)), None)
        if hit is not None:
            matched.append((lvl, title, hit))
    if len(matched) < 0.7 * len(toc):
        return False
    for b in blocks:
        b.level = None
    # A bookmark often points at a block where the heading runs straight into its
    # first paragraph, so split the heading off into its own block. Go bottom-up
    # so inserting doesn't shift indices we still need.
    for lvl, title, i in sorted(matched, key=lambda m: -m[2]):
        b = blocks[i]
        rest = b.text[len(title):].strip()
        b.text, b.level = title, lvl
        if rest:
            blocks.insert(i + 1, Block(rest, b.page, b.size, b.bold, b.y0, b.y1, b.page_height))
    return True


def _normalise_levels(blocks: list[Block]) -> None:
    levels = sorted({b.level for b in blocks if b.is_heading})
    remap = {lvl: i + 1 for i, lvl in enumerate(levels)}
    for b in blocks:
        if b.is_heading:
            b.level = remap[b.level]


def read_pdf(path: str | Path) -> Document:
    path = Path(path)
    with pymupdf.open(path) as pdf:
        blocks = _read_blocks(pdf)
        blocks, removed = _drop_running_text(blocks, pdf.page_count)
        body = _body_size(blocks)
        title, title_size = _find_title(pdf, blocks, body)
        if not _apply_outline(pdf, blocks):
            _assign_levels(blocks, body, title_size)
            blocks = _merge_wrapped_headings(blocks)
        # the title itself is not a section
        blocks = [b for b in blocks if not (title_size and b.page == 1 and b.size == title_size)]
        blocks = [b for b in blocks if not (b.is_heading and b.text == title)]
        _normalise_levels(blocks)
        return Document(title or path.stem.replace("_", " "), blocks, pdf.page_count, body, removed)
