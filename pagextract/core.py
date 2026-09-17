"""
Text extraction that keeps track of *where* the text came from.

Most extractors flatten a document into one long string, which makes it
impossible to say "this sentence is on page 12". ``pagextract`` keeps the
origin of every chunk, so findings can be cited.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import IO, Union

from .models import Block, Document

PathLike = Union[str, Path, IO[bytes]]

__all__ = ["extract", "extract_pdf", "extract_docx", "UnsupportedFormat", "ExtractionError"]


class UnsupportedFormat(ValueError):
    """Raised when the file extension is not handled."""


class ExtractionError(RuntimeError):
    """Raised when a file is recognised but cannot be read."""


# --------------------------------------------------------------------------- #
# optional backends
# --------------------------------------------------------------------------- #

def _pdf_backend():
    """Return a PdfReader class, preferring pypdf and falling back to PyPDF2."""
    try:
        from pypdf import PdfReader  # type: ignore
        return PdfReader, "pypdf"
    except ImportError:
        pass
    try:
        from PyPDF2 import PdfReader  # type: ignore
        return PdfReader, "PyPDF2"
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ExtractionError(
            "No PDF backend available. Install one of: pypdf, PyPDF2"
        ) from exc


def _docx_backend():
    try:
        from docx import Document as DocxDocument  # type: ignore
        return DocxDocument
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ExtractionError(
            "python-docx is required to read .docx files. Install: pip install python-docx"
        ) from exc


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _as_stream(src: PathLike) -> tuple[IO[bytes], str]:
    """Normalise the input to (binary stream, display name)."""
    if isinstance(src, (str, Path)):
        p = Path(src)
        if not p.is_file():
            raise FileNotFoundError(f"No such file: {p}")
        return io.BytesIO(p.read_bytes()), p.name
    name = getattr(src, "name", "<stream>")
    if hasattr(src, "seek"):
        src.seek(0)
    return src, str(name)


def _suffix(src: PathLike) -> str:
    if isinstance(src, (str, Path)):
        return Path(src).suffix.lower()
    return Path(str(getattr(src, "name", ""))).suffix.lower()


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #

def extract_pdf(src: PathLike, *, max_pages: int | None = None) -> Document:
    """
    Extract text from a PDF, one :class:`Block` per page.

    Parameters
    ----------
    src:
        Path or binary stream.
    max_pages:
        Stop after this many pages. ``None`` (default) reads the whole file.
        When a limit truncates the document, ``Document.truncated`` is ``True``
        and ``Document.total_units`` holds the real page count -- the caller is
        never left guessing whether content was silently dropped.
    """
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be >= 1 or None")

    PdfReader, backend = _pdf_backend()
    stream, name = _as_stream(src)
    doc = Document(source=name, fmt="pdf")

    try:
        reader = PdfReader(stream)
    except Exception as exc:
        raise ExtractionError(f"Cannot read PDF {name!r}: {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            pass
        doc.warnings.append("PDF is encrypted; extraction may be incomplete")

    total = len(reader.pages)
    doc.total_units = total
    limit = total if max_pages is None else min(max_pages, total)
    doc.truncated = limit < total
    if doc.truncated:
        doc.warnings.append(
            f"stopped at page {limit} of {total} (max_pages={max_pages})"
        )

    for i in range(limit):
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception as exc:
            text = ""
            doc.warnings.append(f"page {i + 1}: {type(exc).__name__}: {exc}")
        doc.blocks.append(
            Block(text=text.strip(), locator=f"p. {i + 1}", kind="page", index=i + 1)
        )

    if total and not doc.non_empty():
        doc.warnings.append(
            "no text layer found -- the PDF is probably a scan; OCR is required"
        )
    doc.warnings.append(f"backend: {backend}")
    return doc


# --------------------------------------------------------------------------- #
# DOCX
# --------------------------------------------------------------------------- #

def extract_docx(src: PathLike, *, include_tables: bool = True) -> Document:
    """
    Extract text from a .docx file.

    Paragraphs and (optionally) tables are returned as separate blocks. Tables
    are included by default because in technical documents they frequently carry
    the substance -- schedules, specifications, bills of quantities.

    .docx has no fixed pagination before rendering, so blocks are located by
    flow position (``para 12``, ``table 3``) rather than by page number.
    """
    DocxDocument = _docx_backend()
    stream, name = _as_stream(src)
    doc = Document(source=name, fmt="docx")

    try:
        d = DocxDocument(stream)
    except Exception as exc:
        raise ExtractionError(f"Cannot read DOCX {name!r}: {exc}") from exc

    for i, para in enumerate(d.paragraphs, start=1):
        doc.blocks.append(
            Block(text=para.text.strip(), locator=f"para {i}", kind="paragraph", index=i)
        )

    if include_tables:
        for t, table in enumerate(d.tables, start=1):
            rows = []
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                if any(cells):
                    rows.append(" | ".join(cells))
            doc.blocks.append(
                Block(text="\n".join(rows), locator=f"table {t}", kind="table", index=t)
            )

    doc.total_units = len(doc.blocks)
    doc.warnings.append(
        "locators are flow positions, not page numbers (.docx has no fixed pages)"
    )
    return doc


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #

def extract(src: PathLike, **kwargs) -> Document:
    """
    Extract from a .pdf or .docx file, picking the right reader by extension.

    Extra keyword arguments are forwarded to the format-specific function
    (``max_pages`` for PDF, ``include_tables`` for DOCX).
    """
    ext = _suffix(src)
    if ext == ".pdf":
        return extract_pdf(src, **kwargs)
    if ext == ".docx":
        return extract_docx(src, **kwargs)
    if ext == ".doc":
        raise UnsupportedFormat(
            ".doc (Word 97-2003) is not supported -- convert it to .docx or PDF first"
        )
    raise UnsupportedFormat(f"Unsupported extension {ext!r}; expected .pdf or .docx")
