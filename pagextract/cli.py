"""Command-line interface for pagextract."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core import ExtractionError, UnsupportedFormat, extract


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pagextract",
        description="Extract text from PDF/DOCX while keeping track of where it came from.",
        epilog="Examples:\n"
               "  pagextract report.pdf\n"
               "  pagextract report.pdf --max-pages 10 --format json\n"
               "  pagextract spec.docx --find 'evacuation exit'\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("file", help="path to a .pdf or .docx file")
    p.add_argument("--max-pages", type=int, default=None,
                   help="stop after N pages (PDF only)")
    p.add_argument("--no-tables", action="store_true",
                   help="skip tables (DOCX only)")
    p.add_argument("--find", metavar="TEXT",
                   help="print only blocks containing TEXT, with their locator")
    p.add_argument("--format", choices=("text", "json", "summary"), default="text",
                   help="output format (default: text)")
    p.add_argument("--quiet", action="store_true", help="suppress warnings on stderr")
    p.add_argument("--version", action="version", version=f"pagextract {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    kwargs = {}
    if args.file.lower().endswith(".pdf"):
        kwargs["max_pages"] = args.max_pages
    elif args.file.lower().endswith(".docx"):
        kwargs["include_tables"] = not args.no_tables

    try:
        doc = extract(args.file, **kwargs)
    except (UnsupportedFormat, ExtractionError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        for w in doc.warnings:
            print(f"warning: {w}", file=sys.stderr)

    blocks = doc.find(args.find) if args.find else doc.non_empty()

    if args.format == "json":
        payload = doc.to_dict()
        if args.find:
            payload["blocks"] = [
                {"text": b.text, "locator": b.locator, "kind": b.kind, "index": b.index}
                for b in blocks
            ]
            payload["query"] = args.find
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.format == "summary":
        print(f"source      : {doc.source}")
        print(f"format      : {doc.fmt}")
        print(f"blocks      : {len(doc)} ({len(doc.non_empty())} non-empty)")
        print(f"total units : {doc.total_units}")
        print(f"truncated   : {doc.truncated}")
        print(f"characters  : {doc.char_count}")
        if args.find:
            print(f"matches for {args.find!r}: {[b.locator for b in blocks] or 'none'}")
    else:
        if args.find and not blocks:
            print(f"(no block contains {args.find!r})")
        for b in blocks:
            print(f"--- {b.locator} ---")
            print(b.text)
            print()

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
