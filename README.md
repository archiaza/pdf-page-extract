# pagextract

**Text extraction from PDF and DOCX that remembers where the text was.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![Tests](https://img.shields.io/badge/tests-28%20passing-success)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

---

## The problem

Most text extractors hand you one long string:

```python
text = some_extractor("report.pdf")
# 40 000 characters, and no idea where any of it came from
```

That is fine for search indexing and useless for review work. The moment you
find something in a 200-page document, the next question is always **"where?"** —
and a flat string cannot answer it.

The same libraries also tend to fail quietly:

- a page limit silently drops the rest of the file
- a scanned PDF returns `""` and looks identical to an empty one
- DOCX tables are skipped, taking the schedules and specifications with them

## What this does

`pagextract` returns **blocks that carry their own location**, and it is loud
about anything it could not do.

```python
from pagextract import extract

doc = extract("report.pdf")

doc.locate("evacuation exit")      # ['p. 12', 'p. 47']
len(doc)                           # 128 pages
doc.truncated                      # False
```

Every finding can be cited back to its source.

## Install

```bash
git clone https://github.com/archiaza/pdf-page-extract.git
cd pdf-page-extract
pip install -r requirements.txt
```

Requires Python 3.10+.

## Usage

### Library

```python
from pagextract import extract

doc = extract("specification.pdf")

print(doc.fmt)          # 'pdf'
print(len(doc))         # number of blocks
print(doc.char_count)   # total characters

# every block knows its own origin
for block in doc:
    print(block.locator, block.kind, len(block))
    # p. 1   page   1843

# find text and keep the location
for block in doc.find("fire compartment"):
    print(f"{block.locator}: {block.text[:80]}")

# just the locations
doc.locate("fire compartment")     # ['p. 34', 'p. 35']
```

### Page limits are explicit

A limit never hides what it dropped:

```python
doc = extract("large.pdf", max_pages=30)

doc.truncated      # True
len(doc)           # 30
doc.total_units    # 412   <- the real size stays visible
doc.warnings       # ['stopped at page 30 of 412 (max_pages=30)', 'backend: pypdf']
```

### DOCX, including tables

```python
doc = extract("note.docx")

doc.locate("Server room")          # ['table 1']

[b for b in doc if b.kind == "table"]
```

Tables are read by default — in technical documents they usually hold the
substance. Pass `include_tables=False` to skip them.

`.docx` has no fixed pagination until a word processor renders it, so blocks are
located by flow position (`para 12`, `table 3`) rather than by an invented page
number. The library says so in `doc.warnings` instead of guessing.

### Command line

```bash
pagextract report.pdf                                # dump text with locators
pagextract report.pdf --format summary               # counts only
pagextract report.pdf --max-pages 10 --format json   # machine-readable
pagextract spec.docx --find "evacuation exit"        # search with locations
pagextract spec.docx --no-tables                     # skip tables
```

Example:

```
$ pagextract report.pdf --find "evacuation exit"
--- p. 4 ---
Page 4
The evacuation exit door is 0.8 m wide.
```

## API

### `extract(src, **kwargs) -> Document`

Dispatches on file extension. Accepts a path or a binary stream.
Forwards `max_pages` to PDF, `include_tables` to DOCX.

### `Document`

| Member | Meaning |
|---|---|
| `blocks` | list of `Block` |
| `fmt` | `"pdf"` or `"docx"` |
| `truncated` | whether a limit dropped content |
| `total_units` | real size before any limit |
| `warnings` | everything the extractor could not do cleanly |
| `text` | all non-empty blocks joined |
| `char_count` | total characters |
| `find(needle)` | blocks containing `needle` |
| `locate(needle)` | locators of those blocks |
| `non_empty()` | blocks with actual content |
| `to_dict()` | JSON-ready structure |

### `Block`

| Field | Meaning |
|---|---|
| `text` | the extracted text |
| `locator` | `"p. 12"`, `"para 34"`, `"table 2"` |
| `kind` | `"page"` \| `"paragraph"` \| `"table"` |
| `index` | 1-based position within its kind |
| `is_empty` | whitespace-only check |

### Errors

| Exception | Raised when |
|---|---|
| `UnsupportedFormat` | extension is not `.pdf` or `.docx` |
| `ExtractionError` | file is recognised but unreadable |
| `FileNotFoundError` | path does not exist |

A corrupted file raises rather than returning `""` — a broken document should
never be indistinguishable from an empty one.

## Examples

```bash
python examples/basic_usage.py     # PDF: locators, search, truncation
python examples/find_in_docx.py    # DOCX: tables, flow positions
```

Both build their own sample files, so they run with no input.

## Tests

```bash
pip install pytest
python -m pytest -v
```

28 tests covering page mapping, truncation reporting, table handling, stream
input, corrupted files, format dispatch and the CLI.

## Design notes

**Locators are honest.** PDF pages are real; DOCX flow positions are not pages
and are never labelled as such.

**Failure is visible.** Truncation sets a flag, a missing text layer produces a
warning, a broken file raises. Nothing important happens silently.

**Backends are optional.** `pypdf` is preferred and `PyPDF2` is accepted; the
one in use is reported in `warnings`.

**No heavy dependencies.** Standard library plus one PDF reader and
`python-docx`.

## Limitations

- No OCR — scanned PDFs without a text layer yield empty blocks and a warning
- No bounding boxes yet; locators are page-level, not coordinate-level
- `.doc` (Word 97-2003) is not supported; convert to `.docx` or PDF
- Reading order follows the PDF's internal order, which can differ from visual
  order in complex multi-column layouts

## License

MIT — see [LICENSE](LICENSE).
