"""LLM baseline: ask Gemini for the whole mind map in one call.

This is what the original AutoMap did. It is kept as a baseline to compare the
structural pipeline against, not as the main method. Results are cached on disk
so the evaluation is reproducible and doesn't re-spend tokens.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import time
from pathlib import Path

import pymupdf

try:  # read .env so GOOGLE_API_KEY / AUTOMAP_LLM_MODEL can live there
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

MODEL = os.getenv("AUTOMAP_LLM_MODEL", "gemini-3.5-flash-lite")
CACHE = Path(".cache/llm")
PROMPT = """You are building a mind map of a document for a student revising it.
Return JSON only, shaped as {{"title": str, "children": [{{"label": str, "children": [...]}}]}}.
Rules: at most 3 levels below the title; labels are 1-6 words; cover every major part of the document.

Document:
{text}"""


def _text(pdf: Path) -> str:
    with pymupdf.open(pdf) as doc:
        return "\n".join(page.get_text() for page in doc)


def _to_mindmap(raw: dict) -> dict:
    ids = itertools.count()

    def node(d: dict, kind: str) -> dict:
        out = {"id": f"l{next(ids)}", "label": str(d.get("label") or d.get("title") or "").strip(), "kind": kind}
        kids = [node(c, "topic") for c in d.get("children", []) if isinstance(c, dict)]
        if kids:
            out["children"] = kids
        return out

    root = node(raw, "document")
    return {"title": root["label"], "root": root, "passages": [], "links": [], "stats": {"method": f"llm:{MODEL}"}}


def llm_mindmap(pdf: str | Path, use_cache: bool = True) -> dict:
    pdf = Path(pdf)
    text = _text(pdf)
    key = hashlib.sha256(f"{MODEL}\n{PROMPT}\n{text}".encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.json"
    if use_cache and cached.exists():
        return _to_mindmap(json.loads(cached.read_text(encoding="utf-8")))

    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("Set GOOGLE_API_KEY (see .env.example) to run the LLM baseline.")
    from google import genai  # optional dependency: pip install -e .[llm]

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=PROMPT.format(text=text),
                config={"response_mime_type": "application/json", "temperature": 0.2},
            )
            break
        except genai.errors.ServerError:  # 503 "high demand" is common; back off and retry
            if attempt == 3:
                raise
            time.sleep(5 * 2**attempt)
    raw = json.loads(response.text)
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    return _to_mindmap(raw)
