"""
Basic usage of pagextract.

Run:  python examples/basic_usage.py
It builds a small sample PDF, then shows what extraction gives you.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pagextract import extract  # noqa: E402


def build_sample_pdf(path: Path) -> Path:
    """Create a 6-page PDF so the example is self-contained."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    body = {
        1: "Title page. Project documentation, section AR.",
        2: "General provisions. Building class II.",
        3: "Room height is 2.5 m in the office area.",
        4: "The evacuation exit door is 0.8 m wide.",
        5: "Fire compartment area does not exceed 2000 m2.",
        6: "Appendix A. List of applied standards.",
    }
    c = canvas.Canvas(str(path), pagesize=A4)
    for page, text in body.items():
        c.drawString(72, 800, f"Page {page}")
        c.drawString(72, 770, text)
        c.showPage()
    c.save()
    return path


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    pdf = build_sample_pdf(tmp / "sample.pdf")

    # ---- 1. extract everything -------------------------------------------
    doc = extract(pdf)
    print(f"source     : {doc.source}")
    print(f"format     : {doc.fmt}")
    print(f"pages      : {len(doc)}")
    print(f"characters : {doc.char_count}")
    print(f"truncated  : {doc.truncated}")
    print()

    # ---- 2. every block knows where it came from -------------------------
    print("First three blocks:")
    for block in list(doc)[:3]:
        preview = block.text.replace("\n", " ")[:60]
        print(f"  [{block.locator:>6}] {preview}")
    print()

    # ---- 3. the point of the library: citable findings -------------------
    for phrase in ("evacuation exit", "2.5 m", "fire compartment"):
        where = doc.locate(phrase)
        print(f"{phrase!r:22} -> {where or 'not found'}")
    print()

    # ---- 4. truncation is explicit, never silent -------------------------
    limited = extract(pdf, max_pages=2)
    print(f"with max_pages=2 : {len(limited)} of {limited.total_units} pages, "
          f"truncated={limited.truncated}")
    for w in limited.warnings:
        print(f"  warning: {w}")


if __name__ == "__main__":
    main()
