"""Segmentation: paragraphs, sentences and report sections, all with character offsets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from spacy.tokens import Doc, Span

from app.core.nlp import parse

# Canonical report sections (CLAUDE.md §9.5) and the heading words that map to them.
SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "abstract": ("abstract", "summary", "executive summary"),
    "introduction": ("introduction", "overview", "background and motivation", "motivation"),
    "objectives": (
        "objectives",
        "objective",
        "aims",
        "aim",
        "aims and objectives",
        "goals",
        "problem statement",
        "scope",
    ),
    "theory": (
        "theory",
        "background",
        "theoretical background",
        "literature review",
        "literature survey",
        "related work",
        "principle",
        "principles",
        "working principle",
        "theoretical framework",
        "fundamentals",
    ),
    "methodology": (
        "methodology",
        "method",
        "methods",
        "materials and methods",
        "experimental setup",
        "experimental procedure",
        "procedure",
        "experiment",
        "apparatus",
        "design",
        "implementation",
        "system design",
        "proposed system",
        "approach",
        "experimental method",
        "test setup",
    ),
    "results": (
        "results",
        "observations",
        "observation",
        "findings",
        "readings",
        "calculations",
        "observations and calculations",
        "results and analysis",
        "analysis",
        "data",
    ),
    "discussion": (
        "discussion",
        "results and discussion",
        "analysis and discussion",
        "evaluation",
        "interpretation",
    ),
    "conclusion": (
        "conclusion",
        "conclusions",
        "conclusion and future work",
        "conclusions and future work",
        "future work",
        "future scope",
        "concluding remarks",
        "summary and conclusion",
        "inference",
    ),
    "references": ("references", "bibliography", "works cited", "citations"),
    "appendix": ("appendix", "appendices"),
    "acknowledgements": ("acknowledgements", "acknowledgments", "acknowledgement"),
}
_ALIAS_TO_SECTION = {alias: name for name, aliases in SECTION_ALIASES.items() for alias in aliases}

_NUMBERING_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:(?:[0-9]+|[IVXivx]+|[A-Z])(?:\.[0-9]+)*[.)]?\s+)?"
)
_TRAILING_RE = re.compile(r"[\s:.\-–—]+$")


@dataclass(frozen=True)
class Paragraph:
    index: int
    start: int
    end: int
    text: str
    is_heading: bool = False


@dataclass(frozen=True)
class Section:
    name: str  # canonical name, or "other" / "body"
    heading: str
    start: int
    end: int


@dataclass
class Sentence:
    index: int
    start: int
    end: int
    text: str
    paragraph: int
    section: str
    span: Span = field(repr=False)

    @property
    def words(self) -> int:
        return sum(1 for t in self.span if not (t.is_punct or t.is_space))


@dataclass
class Segmentation:
    text: str
    doc: Doc
    paragraphs: list[Paragraph]
    sentences: list[Sentence]
    sections: list[Section]

    def section_at(self, offset: int) -> str:
        for s in self.sections:
            if s.start <= offset < s.end:
                return s.name
        return "body"

    def sentences_in(self, paragraph: int) -> list[Sentence]:
        return [s for s in self.sentences if s.paragraph == paragraph]

    @property
    def body_sentences(self) -> list[Sentence]:
        """Sentences that are not headings and not in the reference list."""
        headings = {p.index for p in self.paragraphs if p.is_heading}
        return [
            s
            for s in self.sentences
            if s.paragraph not in headings and s.section not in ("references",)
        ]


def canonical_section(heading: str) -> str | None:
    """Map a heading line to a canonical section name, or None if it isn't one we know."""
    h = _NUMBERING_RE.sub("", heading.strip(), count=1)
    h = _TRAILING_RE.sub("", h).lower().replace("&", "and").strip()
    if h in _ALIAS_TO_SECTION:
        return _ALIAS_TO_SECTION[h]
    for alias, name in _ALIAS_TO_SECTION.items():
        if h.startswith(alias + " ") and len(h.split()) <= 6:
            return name
    return None


def looks_like_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 90:
        return False
    if s.startswith("#"):
        return True
    if canonical_section(s):
        return True
    words = s.split()
    if len(words) > 10 or s[-1] in ".?!,;" or (s.endswith(":") and len(words) > 6):
        return False
    numbered = bool(re.match(r"^(?:[0-9]+(?:\.[0-9]+)*|[IVX]+)[.)]?\s+[A-Z]", s))
    title_case = sum(w[0].isupper() for w in words if w[0].isalpha()) >= max(1, len(words) * 0.6)
    return numbered or (s.isupper() and len(words) <= 8) or (title_case and len(words) <= 6)


def split_paragraphs(text: str) -> list[Paragraph]:
    """Blank-line separated blocks; single lines inside a block that look like headings are
    split out. When a text has no blank lines at all, every line is a paragraph."""
    has_blank = re.search(r"\n[ \t]*\n", text) is not None
    paragraphs: list[Paragraph] = []
    block_re = re.compile(r"(?:[^\n]|\n(?![ \t]*\n))+") if has_blank else re.compile(r"[^\n]+")
    for m in block_re.finditer(text):
        block_start = m.start()
        lines = list(re.finditer(r"[^\n]+", m.group()))
        current: tuple[int, int] | None = None
        for ln in lines:
            ls, le = block_start + ln.start(), block_start + ln.end()
            line = text[ls:le]
            if not line.strip():
                continue
            if looks_like_heading(line):
                if current:
                    paragraphs.append(_para(text, len(paragraphs), *current, heading=False))
                    current = None
                paragraphs.append(_para(text, len(paragraphs), ls, le, heading=True))
                continue
            current = (current[0], le) if current else (ls, le)
        if current:
            paragraphs.append(_para(text, len(paragraphs), *current, heading=False))
    return paragraphs


def _para(text: str, index: int, start: int, end: int, heading: bool) -> Paragraph:
    # trim surrounding whitespace so offsets point at real characters
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return Paragraph(index, start, end, text[start:end], heading)


def detect_sections(text: str, paragraphs: list[Paragraph]) -> list[Section]:
    heads = [p for p in paragraphs if p.is_heading]
    sections: list[Section] = []
    if not heads:
        return [Section("body", "", 0, len(text))]
    if heads[0].start > 0 and text[: heads[0].start].strip():
        sections.append(Section("body", "", 0, heads[0].start))
    for i, h in enumerate(heads):
        end = heads[i + 1].start if i + 1 < len(heads) else len(text)
        name = canonical_section(h.text) or "other"
        sections.append(Section(name, h.text.strip(), h.start, end))
    # an unknown sub-heading inherits the previous known section (e.g. "3.2 Circuit design")
    for i, s in enumerate(sections):
        if s.name == "other" and i > 0 and sections[i - 1].name not in ("body", "other"):
            sections[i] = Section(sections[i - 1].name, s.heading, s.start, s.end)
    return sections


@lru_cache(maxsize=64)
def segment(text: str) -> Segmentation:
    doc = parse(text)
    paragraphs = split_paragraphs(text)
    sections = detect_sections(text, paragraphs)
    seg = Segmentation(text, doc, paragraphs, [], sections)
    sentences: list[Sentence] = []
    for p in paragraphs:
        for sent in _sentences_in_range(doc, p.start, p.end):
            sentences.append(
                Sentence(
                    index=len(sentences),
                    start=sent.start_char,
                    end=sent.end_char,
                    text=sent.text,
                    paragraph=p.index,
                    section=seg.section_at(sent.start_char),
                    span=sent,
                )
            )
    seg.sentences = sentences
    return seg


def _sentences_in_range(doc: Doc, start: int, end: int) -> list[Span]:
    out: list[Span] = []
    for sent in doc.sents:
        s, e = max(sent.start_char, start), min(sent.end_char, end)
        if s >= e:
            continue
        span = doc.char_span(s, e, alignment_mode="contract")
        if span is None or not span.text.strip():
            continue
        # strip leading/trailing whitespace tokens
        while len(span) and span[0].is_space:
            span = span[1:]
        while len(span) and span[-1].is_space:
            span = span[:-1]
        if len(span):
            out.append(span)
    return _merge_fragments(doc, out)


def _merge_fragments(doc: Doc, spans: list[Span]) -> list[Span]:
    """spaCy sometimes splits after abbreviations like 'Fig.' or 'et al.'; re-join them."""
    merged: list[Span] = []
    for sp in spans:
        if merged:
            prev = merged[-1]
            prev_last = prev[-1].text
            joins = (
                prev_last
                in {
                    "Fig.",
                    "Figs.",
                    "Eq.",
                    "Eqs.",
                    "al.",
                    "e.g.",
                    "i.e.",
                    "vs.",
                    "approx.",
                    "Ref.",
                    "No.",
                    "Sec.",
                    "Tab.",
                    "cf.",
                    "etc.,",
                }
                or (
                    prev_last == "."
                    and len(prev) >= 2
                    and prev[-2].text in {"Fig", "Eq", "al", "et"}
                )
                or sp[0].is_lower
                or len([t for t in sp if not t.is_punct]) == 0
            )
            if joins:
                merged[-1] = doc[prev.start : sp.end]
                continue
        merged.append(sp)
    return merged
