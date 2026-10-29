"""A synthetic paper with known structure, so parser behaviour can be asserted exactly."""

from pathlib import Path

import pymupdf
import pytest

VISION = (
    "Convolutional neural networks learn image filters for vision tasks. The convolution layers detect edges "
    "and textures in each image, while pooling layers shrink the feature maps. Image classification accuracy "
    "improves as convolution filters stack deeper. "
)
FINANCE = (
    "Option hedging in incomplete markets requires a dynamic hedge ratio. The hedge portfolio tracks the option "
    "price as the stock moves, and hedging error grows when volatility jumps. Traders rebalance the hedge daily. "
)


def _page(doc, header=True):
    page = doc.new_page(width=595, height=842)
    if header:
        page.insert_text((60, 30), "Journal of Synthetic Tests", fontsize=8)
        page.insert_text((290, 820), str(doc.page_count), fontsize=8)
    return page


def _para(page, y, text, size=10):
    rect = pymupdf.Rect(60, y, 535, y + 200)
    page.insert_textbox(rect, text, fontsize=size, fontname="helv")
    return y + 16 + 13 * (len(text) // 85 + 1)


@pytest.fixture(scope="session")
def paper(tmp_path_factory) -> Path:
    doc = pymupdf.open()
    page = _page(doc)
    page.insert_text((60, 90), "A Tale of Two Topics", fontsize=22, fontname="hebo")
    page.insert_text((60, 115), "Ada Author, University of Testing", fontsize=10)
    y = 150
    page.insert_text((60, y), "Abstract", fontsize=14, fontname="hebo")
    y = _para(page, y + 8, VISION[:200] + FINANCE[:200])
    page.insert_text((60, y + 10), "1. Image models", fontsize=14, fontname="hebo")
    y = y + 18
    for _ in range(4):
        y = _para(page, y, VISION)
    page = _page(doc)
    y = 70
    page.insert_text((60, y), "2. Hedging", fontsize=14, fontname="hebo")
    y += 8
    page.insert_text((60, y + 14), "2.1 Dynamic hedge", fontsize=11, fontname="hebo")
    y += 22
    for _ in range(4):
        y = _para(page, y, FINANCE)
    page = _page(doc)
    page.insert_text((60, 70), "References", fontsize=14, fontname="hebo")
    _para(page, 80, "[1] Someone. A cited work about nothing in particular. 2020.")
    path = tmp_path_factory.mktemp("pdf") / "paper.pdf"
    doc.save(path)
    return path
