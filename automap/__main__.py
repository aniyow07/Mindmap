"""Command line: `python -m automap build paper.pdf -o map.json`, `python -m automap eval samples/*.pdf`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _outline(node: dict, links: list[dict], depth: int = 0) -> None:
    kw = ", ".join(node.get("keywords", [])[:3])
    print(f"{'  ' * depth}{'•' if depth else '#'} {node['label']}" + (f"  [{kw}]" if kw else ""))
    for c in node.get("children", []):
        _outline(c, links, depth + 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="automap", description="Turn a PDF into an interactive mind map.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a mind map JSON from a PDF")
    b.add_argument("pdf", type=Path)
    b.add_argument("-o", "--out", type=Path, help="write JSON here (default: print an outline)")
    b.add_argument("--method", choices=["automap", "llm"], default="automap")
    b.add_argument("--embedder", choices=["auto", "minilm", "tfidf"], default="auto")

    e = sub.add_parser("eval", help="score AutoMap against baselines on a set of PDFs")
    e.add_argument("pdfs", type=Path, nargs="+")
    e.add_argument("--llm", action="store_true", help="include the Gemini baseline (needs GOOGLE_API_KEY)")
    e.add_argument("-o", "--out", type=Path, help="write the markdown report here")

    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.cmd == "build":
        if args.method == "llm":
            from .llm import llm_mindmap

            data = llm_mindmap(args.pdf)
        else:
            from .mindmap import build_mindmap

            data = build_mindmap(args.pdf, embedder=args.embedder).to_dict()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"wrote {args.out}  {data.get('stats', {})}")
        else:
            _outline(data["root"], data.get("links", []))
            print(json.dumps(data.get("stats", {})))
        return 0

    if args.cmd == "eval":
        from .evaluate import run_eval

        report = run_eval(args.pdfs, include_llm=args.llm)
        if args.out:
            args.out.write_text(report, encoding="utf-8")
        print(report)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
