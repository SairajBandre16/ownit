"""Protected-span detection (CLAUDE.md §6.1). Transforms may never touch these characters."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from app.core.nlp import zipf
from app.core.resources import load
from app.core.segment import Segmentation, segment
from app.core.spans import SpanIndex

# priority when overlapping spans are merged for display (lower = wins)
KIND_PRIORITY = [
    "code",
    "equation",
    "quote",
    "citation",
    "reference",
    "url",
    "number",
    "abbreviation",
    "entity",
    "keep",
    "term",
]
ENTITY_LABELS = {"ORG", "PERSON", "GPE", "PRODUCT", "LAW", "WORK_OF_ART"}


@dataclass(frozen=True)
class Protected:
    start: int
    end: int
    kind: str
    text: str


# ---------------------------------------------------------------- regexes
QUOTE_RE = re.compile(r"\"[^\"\n]{1,400}\"|“[^”\n]{1,400}”")
CITATION_RE = re.compile(
    r"\((?:see\s+)?(?:[A-Z][\w\-’']+(?:\s+(?:et\s+al\.?|and|&)\s*(?:[A-Z][\w\-’']+)?)?,?\s+"
    r"(?:\d{4}[a-z]?|n\.d\.)(?:,\s*(?:p|pp)\.\s*\d+(?:[–-]\d+)?)?(?:;\s*)?)+\)"
    r"|\[\d+(?:\s*[–,\-]\s*\d+)*\]"
    r"|\b[A-Z][\w\-’']+(?:\s+et\s+al\.|\s+(?:and|&)\s+[A-Z][\w\-’']+)?\s+\(\d{4}[a-z]?\)"
)
LATEX_RE = re.compile(r"\$\$.+?\$\$|\$[^$\n]+\$|\\\(.+?\\\)|\\\[.+?\\\]", re.DOTALL)
_TERM = r"[A-Za-z0-9_().^²³√πθαβγδΔωΩλμσητφ'·₀-₉]+"
_OP = r"[=+\-−*/×·^<>≤≥≈÷]"
EQUATION_RE = re.compile(rf"{_TERM}(?:\s*{_OP}\s*{_TERM})+")
REL_RE = re.compile(r"[=≈≤≥<>]")
FIG_RE = re.compile(
    r"\b(?:Fig(?:ure)?s?\.?|Tab(?:le)?s?\.?|Eqs?\.|Equations?|Sec(?:tion)?s?\.?|Appendix|Chapter|Ref\.)"
    r"\s*\(?\d+(?:\.\d+)*\)?(?:\s*\(?[a-z]\))?(?:\s*(?:and|&|–|-|to)\s*\(?\d+(?:\.\d+)*\)?)?",
)
CODE_SPAN_RE = re.compile(r"`[^`\n]+`|```.*?```", re.DOTALL)
CODE_LINE_RE = re.compile(
    r"^[ \t]*(?:def |class |import |from \S+ import|#include|for\s*\(|while\s*\(|if\s*\(|return\b|"
    r"public |private |void |int |float |double |char |printf|print\(|console\.|//|/\*|\}|\{|"
    r"[A-Za-z_]\w*\s*\(.*\)\s*;|[A-Za-z_][\w.\[\]]*\s*(?:=|\+=|-=)\s*[^=].*;)\s*.*$",
    re.MULTILINE,
)
URL_RE = re.compile(r"\bhttps?://\S+|\bwww\.\S+|\b[\w.+-]+@[\w-]+\.[\w.]+")
ABBR_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,5}s?\b|\b[A-Z][a-z]?[A-Z][A-Za-z0-9]*\b")
NUMBER = (
    r"(?:[±+\-−~≈]\s?)?\d+(?:[.,]\d+)*(?:\s?(?:×|x|\*)\s?10\^?[−\-]?\d+|\^[−\-]?\d+|e[−\-]?\d+)?"
)


@lru_cache(maxsize=1)
def _unit_re() -> re.Pattern[str]:
    data = load("si_units")
    symbols = {u["symbol"] for u in data["units"]}
    symbols |= {k for k in data["miscased"]} | set(data["plurals"])
    alts = "|".join(re.escape(s) for s in sorted(symbols, key=len, reverse=True))
    return re.compile(
        rf"{NUMBER}(?:\s?(?:–|-|to)\s?{NUMBER})?\s?(?:{alts})(?![A-Za-z0-9])|{NUMBER}\s?%|10\^[−\-]?\d+"
    )


NUM_RE = re.compile(rf"(?<![\w.]){NUMBER}(?![\w])")


@lru_cache(maxsize=1)
def _known_abbreviations() -> frozenset[str]:
    return frozenset(load("eng_abbreviations"))


# ---------------------------------------------------------------- detectors
def _regex_spans(text: str, rx: re.Pattern[str], kind: str) -> list[Protected]:
    return [
        Protected(m.start(), m.end(), kind, m.group())
        for m in rx.finditer(text)
        if m.group().strip()
    ]


def _equations(text: str) -> list[Protected]:
    out = _regex_spans(text, LATEX_RE, "equation")
    for m in EQUATION_RE.finditer(text):
        expr = m.group()
        if not REL_RE.search(expr):
            continue
        # "state-of-the-art" or "a-b" style hyphenations are not equations
        if not re.search(r"\d|[=≈≤≥]\s*\S", expr):
            continue
        out.append(Protected(m.start(), m.end(), "equation", expr))
    # a whole line that is mostly maths
    for m in re.finditer(r"[^\n]+", text):
        line = m.group()
        if "=" in line and re.search(r"[+\-*/^√∑∫×÷]|\d", line):
            words = re.findall(r"[A-Za-z]{3,}", line)
            if len(words) <= 2 and len(line) < 120:
                out.append(Protected(m.start(), m.end(), "equation", line))
    return out


def _abbreviations(text: str) -> list[Protected]:
    known = _known_abbreviations()
    out = []
    for m in ABBR_RE.finditer(text):
        tok = m.group()
        base = tok[:-1] if tok.endswith("s") and tok[:-1].isupper() else tok
        letters = sum(c.isalpha() for c in base)
        if (
            base in known
            or (base.isupper() and 2 <= letters <= 6)
            or (any(c.isupper() for c in base[1:]) and len(base) <= 8)
        ):
            out.append(Protected(m.start(), m.end(), "abbreviation", tok))
    for abbr in known:
        if not abbr.isupper():
            for m in re.finditer(rf"(?<![\w-]){re.escape(abbr)}(?![\w-])", text):
                out.append(Protected(m.start(), m.end(), "abbreviation", m.group()))
    return out


def _entities(seg: Segmentation) -> list[Protected]:
    return [
        Protected(e.start_char, e.end_char, "entity", e.text)
        for e in seg.doc.ents
        if e.label_ in ENTITY_LABELS
    ]


def _occurrences(text: str, phrase: str, kind: str) -> list[Protected]:
    if not phrase.strip():
        return []
    rx = re.compile(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", re.IGNORECASE)
    return [Protected(m.start(), m.end(), kind, m.group()) for m in rx.finditer(text)]


def keyphrases(text: str, top: int | None = None) -> list[str]:
    """YAKE keyphrases (lowercase), best first."""
    import yake

    n_words = len(text.split())
    if n_words < 8:
        return []
    k = top or min(20, 5 + n_words // 40)
    extractor = yake.KeywordExtractor(lan="en", n=3, dedupLim=0.8, top=k)
    phrases = [kw.strip(" .,;:!?()[]\"'") for kw, _ in extractor.extract_keywords(text)]
    return [p.lower() for p in phrases if any(c.isalpha() for c in p)]


def repeated_chunks(seg: Segmentation) -> list[str]:
    """Noun chunks (without determiners) that occur at least twice and look technical."""
    counts: Counter[str] = Counter()
    surfaces: dict[str, str] = {}
    for chunk in seg.doc.noun_chunks:
        toks = [
            t
            for t in chunk
            if t.pos_ not in ("DET", "PRON") and t.dep_ != "poss" and not t.is_punct
        ]
        if not toks:
            continue
        key = " ".join(t.lemma_.lower() for t in toks)
        surf = seg.text[toks[0].idx : toks[-1].idx + len(toks[-1])]
        counts[key] += 1
        surfaces.setdefault(key, surf)
    out = []
    for key, n in counts.items():
        if n < 2:
            continue
        words = key.split()
        if len(words) >= 2 or (words and zipf(words[0]) < 4.0 and len(words[0]) > 3):
            out.append(surfaces[key])
    return out


_TERM_POS = {"NOUN", "PROPN", "ADJ", "NUM", "X", "SYM"}


def _is_nominal(seg: Segmentation, start: int, end: int) -> bool:
    """A keyphrase occurrence counts as a term only if it is a noun phrase
    (YAKE sometimes returns fragments like "shown in Fig")."""
    span = seg.doc.char_span(start, end, alignment_mode="expand")
    if span is None or not len(span):
        return False
    toks = [t for t in span if not t.is_punct]
    if not toks or toks[-1].pos_ not in ("NOUN", "PROPN"):
        return False
    first = toks[0]
    if len(toks) == 1 and first.i >= 2:
        to, adj = seg.doc[first.i - 1], seg.doc[first.i - 2]
        if to.lower_ == "to" and adj.pos_ == "ADJ":
            return False  # "simple to tune": a verb the tagger read as a noun
    return all(t.pos_ in _TERM_POS or (t.pos_ == "ADP" and t.lower_ == "of") for t in toks)


STYLE_LEXICONS = ("ai_style_phrases", "wordy_phrases", "cliches", "fillers", "weak_verbs")


def _style_phrase_index(seg: Segmentation) -> SpanIndex:
    """Spans of known stock/wordy phrases: these are never 'technical terms'."""
    from app.core.lexicon import lexicon

    spans = []
    for name in STYLE_LEXICONS:
        spans += [(m.start, m.end) for m in lexicon(name).find(seg.text)]
    return SpanIndex(spans)


def _terms(seg: Segmentation) -> list[Protected]:
    text = seg.text
    out: list[Protected] = []
    style = _style_phrase_index(seg)
    for phrase in keyphrases(text):
        # single very common words are not "technical terms"
        if " " not in phrase and zipf(phrase) >= 5.0:
            continue
        out.extend(
            p
            for p in _occurrences(text, phrase, "term")
            if _is_nominal(seg, p.start, p.end) and not style.overlaps(p.start, p.end)
        )
    for surf in repeated_chunks(seg):
        out.extend(
            p for p in _occurrences(text, surf, "term") if not style.overlaps(p.start, p.end)
        )
    return out


# ---------------------------------------------------------------- public API
def detect_protected(text: str, keep_terms: tuple[str, ...] = ()) -> list[Protected]:
    """All protected spans, merged so they don't overlap (higher-priority kind wins)."""
    return list(_detect_cached(text, tuple(sorted(set(keep_terms)))))


@lru_cache(maxsize=64)
def _detect_cached(text: str, keep_terms: tuple[str, ...]) -> tuple[Protected, ...]:
    seg = segment(text)
    raw: list[Protected] = []
    raw += _regex_spans(text, CODE_SPAN_RE, "code")
    raw += [p for p in _regex_spans(text, CODE_LINE_RE, "code") if ";" in p.text or "(" in p.text]
    raw += _equations(text)
    raw += _regex_spans(text, QUOTE_RE, "quote")
    raw += _regex_spans(text, CITATION_RE, "citation")
    raw += _regex_spans(text, FIG_RE, "reference")
    raw += _regex_spans(text, URL_RE, "url")
    numbers = _regex_spans(text, _unit_re(), "number") + _regex_spans(text, NUM_RE, "number")
    raw += numbers
    raw += _abbreviations(text)
    # spaCy sometimes reads unit symbols as places ("Pa." -> Pennsylvania); units win
    num_index = SpanIndex((n.start, n.end) for n in numbers)
    raw += [e for e in _entities(seg) if not num_index.overlaps(e.start, e.end)]
    for term in keep_terms:
        raw += _occurrences(text, term, "keep")
    raw += _terms(seg)
    return tuple(_merge(raw))


def _merge(spans: list[Protected]) -> list[Protected]:
    prio = {k: i for i, k in enumerate(KIND_PRIORITY)}
    ordered = sorted(spans, key=lambda p: (p.start, -p.end))
    merged: list[Protected] = []
    for p in ordered:
        if p.end <= p.start:
            continue
        if merged and p.start < merged[-1].end:
            last = merged[-1]
            end = max(last.end, p.end)
            kind = last.kind if prio.get(last.kind, 99) <= prio.get(p.kind, 99) else p.kind
            merged[-1] = Protected(last.start, end, kind, "")
        else:
            merged.append(p)
    return merged


def fill_text(spans: list[Protected], text: str) -> list[Protected]:
    return [Protected(p.start, p.end, p.kind, text[p.start : p.end]) for p in spans]


def protected_index(text: str, keep_terms: tuple[str, ...] = ()) -> SpanIndex:
    return SpanIndex((p.start, p.end) for p in detect_protected(text, keep_terms))


def protected_spans(text: str, keep_terms: tuple[str, ...] = ()) -> list[Protected]:
    """Merged protected spans with their text filled in (for API responses)."""
    return fill_text(detect_protected(text, keep_terms), text)
