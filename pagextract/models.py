"""Data structures returned by the extractors."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterator


@dataclass(frozen=True)
class Block:
    """
    A single unit of extracted text together with its location.

    ``locator`` is the human-readable origin of the text. Its meaning depends on
    the source format and is stated explicitly so callers never have to guess:

    * PDF  -- ``"p. 12"``      (a real, rendered page)
    * DOCX -- ``"para 34"`` / ``"table 2"``  (a flow position, **not** a page)

    DOCX files have no fixed pagination until a word processor renders them, so
    this library never invents page numbers for them.
    """

    text: str
    locator: str
    kind: str  # "page" | "paragraph" | "table"
    index: int  # 1-based position within its own kind

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    def __len__(self) -> int:
        return len(self.text)


@dataclass
class Document:
    """The result of extracting one file."""

    source: str
    fmt: str  # "pdf" | "docx"
    blocks: list[Block] = field(default_factory=list)
    truncated: bool = False
    total_units: int | None = None  # units available before any limit was applied
    warnings: list[str] = field(default_factory=list)

    # ---------- convenience ----------

    def __iter__(self) -> Iterator[Block]:
        return iter(self.blocks)

    def __len__(self) -> int:
        return len(self.blocks)

    @property
    def text(self) -> str:
        """All non-empty blocks joined by blank lines."""
        return "\n\n".join(b.text for b in self.blocks if not b.is_empty)

    @property
    def char_count(self) -> int:
        return sum(len(b) for b in self.blocks)

    def non_empty(self) -> list[Block]:
        return [b for b in self.blocks if not b.is_empty]

    def find(self, needle: str, *, case_sensitive: bool = False) -> list[Block]:
        """Return every block containing ``needle``, keeping its locator."""
        if case_sensitive:
            return [b for b in self.blocks if needle in b.text]
        low = needle.lower()
        return [b for b in self.blocks if low in b.text.lower()]

    def locate(self, needle: str, *, case_sensitive: bool = False) -> list[str]:
        """Return just the locators of blocks containing ``needle``."""
        return [b.locator for b in self.find(needle, case_sensitive=case_sensitive)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "format": self.fmt,
            "blocks": [asdict(b) for b in self.blocks],
            "truncated": self.truncated,
            "total_units": self.total_units,
            "warnings": self.warnings,
            "char_count": self.char_count,
        }
