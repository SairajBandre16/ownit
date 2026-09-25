"""Key terms per paragraph with definitions from (in order of preference):

1. the document itself — "X is a/an/the …", "X refers to …", "X is defined as …",
   "Full Name (ABBR)";
2. the engineering abbreviation list;
3. WordNet (first noun sense, only when the term is a WordNet entry).

Terms without any definition are returned with definition = None: the student is asked to
define them in their own words (active recall).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.core.nlp import zipf
from app.core.resources import load
from app.core.segment import Segmentation
from app.core.terms import noun_keyphrases

DEF_PATTERNS = [
    r"(?P<term>{t})\s*(?:\([^)]*\)\s*)?(?:is|are)\s+(?:defined\s+as|known\s+as)\s+(?P<def>[^.;]+)",
    r"(?P<term>{t})\s*(?:\([^)]*\)\s*)?(?:refers?\s+to|means)\s+(?P<def>[^.;]+)",
    r"(?P<term>{t})\s*(?:\([^)]*\)\s*)?(?:is|are)\s+(?P<def>(?:a|an|the)\s+[^.;]+)",
]
ABBR_DEF_RE = re.compile(
    r"\b((?:[A-Z][\w-]*\s+){1,6}?(?:[A-Za-z][\w-]*))\s+\(([A-Z][A-Za-z0-9]{1,7})\)"
)
MAX_TERMS = 5


@dataclass
class Term:
    term: str
    start: int
    end: int
    definition: str | None
    source: str | None  # "document" | "abbreviation" | "wordnet" | None


@lru_cache(maxsize=1)
def _abbreviations() -> dict[str, str]:
    return load("eng_abbreviations")  # type: ignore[no-any-return]


def document_definitions(seg: Segmentation) -> dict[str, str]:
    """lowercased term -> definition found in the text."""
    out: dict[str, str] = {}
    for m in ABBR_DEF_RE.finditer(seg.text):
        full, abbr = m.group(1).strip(), m.group(2)
        initials = "".join(w[0] for w in full.split() if w[0].isalpha()).upper()
        abbr_u = abbr.upper()
        if initials.endswith(abbr_u[: len(initials)]) or abbr_u.startswith(initials[:2]):
            out.setdefault(abbr.lower(), full)
            out.setdefault(full.lower(), f"abbreviated as {abbr}")
    return out


def _definition_in_text(term: str, text: str) -> str | None:
    t = re.escape(term)
    for pat in DEF_PATTERNS:
        m = re.search(pat.format(t=t), text, flags=re.IGNORECASE)
        if m:
            d = m.group("def").strip()
            if 3 <= len(d.split()) <= 40:
                return d[:1].lower() + d[1:] if not d[:2].isupper() else d
    return None


@lru_cache(maxsize=4096)
def wordnet_definition(term: str) -> str | None:
    from nltk.corpus import wordnet as wn

    key = term.lower().replace(" ", "_")
    synsets = wn.synsets(key, pos=wn.NOUN)
    if not synsets:
        return None
    # single words are often ambiguous ("pin", "cell"): only trust WordNet for multi-word
    # terms or rare, specialised single words
    if " " not in term and zipf(term) > 3.8:
        return None
    return synsets[0].definition()


def define(term: str, seg: Segmentation, doc_defs: dict[str, str]) -> tuple[str | None, str | None]:
    low = term.lower()
    if low in doc_defs:
        return doc_defs[low], "document"
    d = _definition_in_text(term, seg.text)
    if d:
        return d, "document"
    abbr = next((v for k, v in _abbreviations().items() if k.lower() == low), None)
    if abbr:
        return abbr, "abbreviation"
    wn_def = wordnet_definition(term)
    if wn_def:
        return wn_def, "wordnet"
    return None, None


def paragraph_terms(
    seg: Segmentation, start: int, end: int, doc_defs: dict[str, str]
) -> list[Term]:
    text = seg.text[start:end]
    known = {k.lower() for k in _abbreviations()}
    found: list[tuple[str, int, int]] = []
    # abbreviations used in the paragraph are always key terms
    for m in re.finditer(r"\b[A-Z][A-Za-z0-9]{1,6}\b", text):
        low = m.group().lower()
        if low in known or low in doc_defs:
            found.append((m.group(), start + m.start(), start + m.end()))
    found += noun_keyphrases(seg, start, end, top=8)
    seen: set[str] = set()
    out: list[Term] = []
    for surface, s, e in found:
        low = surface.lower()
        if low in seen:
            continue
        seen.add(low)
        definition, source = define(surface, seg, doc_defs)
        out.append(Term(surface, s, e, definition, source))
        if len(out) >= MAX_TERMS:
            break
    return out
