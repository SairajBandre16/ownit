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
    # "X is a/an …" only: "X is the best …" is a claim, not a definition
    r"(?P<term>{t})\s*(?:\([^)]*\)\s*)?(?:is|are)\s+(?P<def>(?:a|an)\s+[^.;]+)",
]
ABBR_DEF_RE = re.compile(
    r"\b((?:[A-Za-z][\w-]*\s+){0,7}[A-Za-z][\w-]*)\s+\(([A-Z][A-Za-z0-9]{1,7})\)"
)
SMALL_WORDS = {"of", "and", "the", "for", "to", "in", "on", "a", "an", "with"}
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


def expansion_for(words: list[str], abbr: str) -> str | None:
    """Shortest run of trailing words whose initials spell the abbreviation
    ("A programmable logic controller" + "PLC" -> "programmable logic controller")."""
    target = abbr.lower()
    target_upper = "".join(c for c in abbr if c.isupper() or c.isdigit()).lower()
    for n in range(1, len(words) + 1):
        tail = words[-n:]
        if tail[0].lower() in SMALL_WORDS:
            continue
        all_initials = "".join(w[0] for w in tail).lower()
        big_initials = "".join(w[0] for w in tail if w.lower() not in SMALL_WORDS).lower()
        if target in (all_initials, big_initials) or target_upper in (all_initials, big_initials):
            return " ".join(tail)
    return None


def abbreviation_pairs(seg: Segmentation) -> dict[str, str]:
    """ABBR -> full name for every "Full Name (ABBR)" in the text."""
    out: dict[str, str] = {}
    for m in ABBR_DEF_RE.finditer(seg.text):
        full = expansion_for(m.group(1).split(), m.group(2))
        if full:
            out.setdefault(m.group(2), full)
    return out


def document_definitions(seg: Segmentation) -> dict[str, str]:
    """lowercased term -> definition found in the text."""
    out: dict[str, str] = {}
    for abbr, full in abbreviation_pairs(seg).items():
        out.setdefault(abbr.lower(), full)
        out.setdefault(full.lower(), f"abbreviated as {abbr}")
    return out


# the term must head its clause: sentence start or after a determiner, so "congestion" does
# not pick up the definition of "traffic congestion"
TERM_LEAD = r"(?:^|(?<=[.!?:])\s+|(?<![\w-])(?:[Tt]he|[Aa]n?|[Tt]his|[Tt]hese)\s+)"


def _definition_in_text(term: str, text: str) -> str | None:
    # abbreviations match case-sensitively ("IS 1498" must not match the verb "is")
    t = re.escape(term) if term.isupper() else f"(?i:{re.escape(term)})"
    for pat in DEF_PATTERNS:
        m = re.search(TERM_LEAD + pat.format(t=t), text, flags=re.MULTILINE)
        if m:
            d = m.group("def").strip()
            if 3 <= len(d.split()) <= 40:
                return d[:1].lower() + d[1:] if not d[:2].isupper() else d
    return None


# WordNet senses that can describe a technical term; social/body/animal/plant senses cannot
OK_LEXNAMES = {
    "noun.artifact",
    "noun.phenomenon",
    "noun.process",
    "noun.substance",
    "noun.quantity",
    "noun.attribute",
    "noun.cognition",
    "noun.time",
    "noun.state",
    "noun.shape",
    "noun.relation",
    "noun.object",
}
TECH_DOMAINS = {
    "computer science",
    "computing",
    "physics",
    "electronics",
    "engineering",
    "chemistry",
    "mathematics",
    "statistics",
    "geometry",
    "mechanics",
    "biology",
    "biochemistry",
    "genetics",
    "medicine",
}
DOMAIN_RE = re.compile(r"^\(([^)]*)\)\s*")


@lru_cache(maxsize=65536)
def _base(word: str) -> str:
    from nltk.corpus import wordnet as wn

    return wn.morphy(word) or word


def _content_lemmas(text: str) -> set[str]:
    """Cheap bag of content-word base forms (no parse: glosses are short and many)."""
    from spacy.lang.en.stop_words import STOP_WORDS

    words = re.findall(r"[a-z][a-z-]{2,}", text.lower())
    return {_base(w) for w in words if w not in STOP_WORDS}


def _sense_words(synset) -> set[str]:  # type: ignore[no-untyped-def]
    text = " ".join([synset.definition(), *synset.examples()])
    text += " " + " ".join(h.definition() for h in synset.hypernyms())
    return _content_lemmas(text)


@lru_cache(maxsize=4096)
def wordnet_definition(term: str, context: frozenset[str] = frozenset()) -> str | None:
    """WordNet gloss for `term`, choosing the sense by overlap with the paragraph's words
    (simplified Lesk). Conservative: returns None rather than a likely-wrong sense."""
    from nltk.corpus import wordnet as wn

    key = term.lower().replace(" ", "_")
    synsets = wn.synsets(key, pos=wn.NOUN)
    if not synsets:
        return None
    # single words are often ambiguous ("pin", "cell"): only trust WordNet for multi-word
    # terms or rare, specialised single words
    if " " not in term and zipf(term) > 3.8:
        return None
    candidates = []
    for rank, syn in enumerate(synsets):
        if syn.lexname() not in OK_LEXNAMES:
            continue
        m = DOMAIN_RE.match(syn.definition())
        if m and not any(d in m.group(1).lower() for d in TECH_DOMAINS):
            continue  # "(tennis) the final point needed to win a set"
        overlap = len(_sense_words(syn) & context)
        candidates.append((overlap, -rank, syn))
    if not candidates:
        return None
    overlap, neg_rank, best = max(candidates, key=lambda c: (c[0], c[1]))
    if overlap == 0 and len(synsets) > 1:
        return None  # ambiguous and nothing in the paragraph supports any sense
    return DOMAIN_RE.sub("", best.definition())


def define(
    term: str,
    seg: Segmentation,
    doc_defs: dict[str, str],
    context: frozenset[str] = frozenset(),
) -> tuple[str | None, str | None]:
    low = term.lower()
    if low in doc_defs:
        return doc_defs[low], "document"
    d = _definition_in_text(term, seg.text)
    if d:
        return d, "document"
    abbr = next((v for k, v in _abbreviations().items() if k.lower() == low), None)
    if abbr:
        return abbr, "abbreviation"
    wn_def = wordnet_definition(term, context - _content_lemmas(term))
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
    context = frozenset(_content_lemmas(text))
    seen: set[str] = set()
    out: list[Term] = []
    for surface, s, e in found:
        low = surface.lower()
        if low in seen:
            continue
        seen.add(low)
        definition, source = define(surface, seg, doc_defs, context)
        out.append(Term(surface, s, e, definition, source))
        if len(out) >= MAX_TERMS:
            break
    return out
