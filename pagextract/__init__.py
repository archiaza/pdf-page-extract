"""
pagextract -- text extraction from PDF and DOCX that remembers where the text was.

    >>> from pagextract import extract
    >>> doc = extract("report.pdf")
    >>> doc.locate("evacuation exit")
    ['p. 12', 'p. 47']

Most extractors return one flat string, which loses the location of every
finding. ``pagextract`` returns blocks that carry their own locator, so a result
can be cited back to the source.
"""

__version__ = "0.1.0"

from .core import (  # noqa: F401
    ExtractionError,
    UnsupportedFormat,
    extract,
    extract_docx,
    extract_pdf,
)
from .models import Block, Document  # noqa: F401

__all__ = [
    "extract",
    "extract_pdf",
    "extract_docx",
    "Block",
    "Document",
    "UnsupportedFormat",
    "ExtractionError",
    "__version__",
]
