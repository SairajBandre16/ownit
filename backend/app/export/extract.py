"""Text from uploaded .docx and .pdf files (CLAUDE.md §8 /files/extract).

.docx: paragraphs in document order; headings, titles and captions become their own lines;
tables are skipped (their captions are kept) with a warning.
.pdf: the text layer page by page; page numbers and running headers/footers are dropped,
words hyphenated across lines are re-joined, and wrapped lines are merged back into
paragraphs. A PDF without a text layer (a scan) is rejected: there is no OCR.
"""

from __future__ import annotations

import io
import re
from collections import Counter
from dataclasses import dataclass, field

MAX_BYTES = 10 * 1024 * 1024
PDF_WARNING = (
    "Check the text: layout from a PDF (columns, tables, equations) may not come through cleanly."
)
PAGE_BREAK = "\f"
HEADING_STYLES = ("heading", "title", "subtitle")
PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s+)?\d{1,4}(?:\s*(?:/|of)\s*\d{1,4})?\s*$", re.IGNORECASE)
HYPHEN_BREAK_RE = re.compile(r"([a-z])-\n([a-z])")
SENTENCE_END_RE = re.compile(r"[.!?:;][\"'”’)\]]?$")


class ExtractError(ValueError):
    pass


@dataclass
class Extracted:
    text: str
    warnings: list[str] = field(default_factory=list)

    @property
    def words(self) -> int:
        return len(self.text.split())


def extract(filename: str, data: bytes) -> Extracted:
    if len(data) > MAX_BYTES:
        raise ExtractError(f"The file is {len(data) // (1024 * 1024)} MB; the limit is 10 MB.")
    name = filename.lower()
    if name.endswith(".docx"):
        return extract_docx(data)
    if name.endswith(".pdf"):
        return extract_pdf(data)
    raise ExtractError("Only .docx and .pdf files can be uploaded.")


# ---------------------------------------------------------------- .docx
def extract_docx(data: bytes) -> Extracted:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        doc = Document(io.BytesIO(data))
    except Exception as e:  # python-docx raises several error types for broken files
        raise ExtractError("This .docx file could not be read.") from e
    blocks: list[str] = []
    tables = 0
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "tbl":
            Table(child, doc)  # validates the element
            tables += 1
            continue
        if tag != "p":
            continue
        p = Paragraph(child, doc)
        text = " ".join(p.text.split())
        if not text:
            continue
        style = (p.style.name if p.style is not None else "").lower()
        if style.startswith("list"):
            text = f"- {text}"
        blocks.append(text)
    warnings = []
    if tables:
        warnings.append(f"{tables} table(s) were skipped; their captions are kept.")
    if not blocks:
        raise ExtractError("No text found in this .docx file.")
    return Extracted("\n\n".join(blocks), warnings)


# ---------------------------------------------------------------- .pdf
def _running_lines(pages: list[list[str]]) -> set[str]:
    """Lines repeated at the top or bottom of most pages (headers, footers)."""
    if len(pages) < 3:
        return set()
    edge: Counter[str] = Counter()
    for lines in pages:
        for ln in {*lines[:2], *lines[-2:]}:
            key = re.sub(r"\d+", "#", ln.strip().lower())
            if key:
                edge[key] += 1
    return {k for k, n in edge.items() if n >= max(3, len(pages) // 2)}


def _is_heading(line: str) -> bool:
    """Same rule as the segmenter: a known section name, a numbered or title-case short line."""
    from app.core.segment import looks_like_heading

    return looks_like_heading(line)


def reflow(lines: list[str]) -> str:
    """Merge wrapped lines back into paragraphs."""
    paras: list[str] = []
    cur: list[str] = []
    for raw in lines:
        if raw == PAGE_BREAK:
            # a paragraph continues onto the next page unless its sentence ended
            if cur and SENTENCE_END_RE.search(cur[-1]):
                paras.append(" ".join(cur))
                cur = []
            continue
        line = raw.strip()
        if not line:
            if cur:
                paras.append(" ".join(cur))
                cur = []
            continue
        if _is_heading(line) and (not cur or SENTENCE_END_RE.search(cur[-1])):
            if cur:
                paras.append(" ".join(cur))
                cur = []
            paras.append(line)
            continue
        cur.append(line)
        if SENTENCE_END_RE.search(line) and len(line) < 45:
            # a short line ending a sentence usually ends the paragraph
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(p for p in paras if p)


def extract_pdf(data: bytes) -> Extracted:
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [(page.extract_text() or "") for page in pdf.pages]
    except Exception as e:  # pdfminer raises many error types for broken files
        raise ExtractError("This PDF could not be read.") from e
    if not any(p.strip() for p in pages):
        raise ExtractError("This PDF has no text layer (it may be a scan). OwnIt doesn't do OCR.")
    page_lines = [HYPHEN_BREAK_RE.sub(r"\1\2", p).split("\n") for p in pages]
    running = _running_lines(page_lines)
    lines: list[str] = []
    for page in page_lines:
        for ln in page:
            key = re.sub(r"\d+", "#", ln.strip().lower())
            if PAGE_NUMBER_RE.match(ln) or key in running:
                continue
            lines.append(ln)
        lines.append(PAGE_BREAK)
    text = reflow(lines)
    warnings = [PDF_WARNING]
    return Extracted(text, warnings)
