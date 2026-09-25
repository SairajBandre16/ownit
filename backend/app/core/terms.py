"""Key technical terms: YAKE keyphrases filtered to real noun phrases.

A keyphrase counts only if its occurrence in the parsed text is a noun phrase (last token a
noun, the rest nouns/adjectives/numbers or "of"), it isn't part of a stock or wordy phrase
("plays a crucial role"), and it isn't inside maths, code, citations or URLs.
"""

from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

from app.core.nlp import zipf
from app.core.protect import _is_nominal, _style_phrase_index, detect_protected, keyphrases
from app.core.resources import load
from app.core.segment import SECTION_ALIASES, Segmentation
from app.core.spans import SpanIndex

EXCLUDE_KINDS = {"equation", "code", "citation", "url", "number", "quote", "reference"}
SINGLE_WORD_MAX_ZIPF = 4.7  # "motor", "torque" are terms; "results", "students" are not
GENERIC_MODIFIERS = {
    "significant",
    "major",
    "high",
    "low",
    "key",
    "important",
    "essential",
    "fundamental",
    "primary",
    "specific",
    "various",
    "numerous",
    "notable",
    "wide",
    "great",
    "crucial",
    "vital",
    "critical",
    "traditional",
    "modern",
    "recent",
    "close",
    "transparent",
    "increasing",
    "growing",
    "overall",
    "main",
}


@lru_cache(maxsize=1)
def _non_terms() -> frozenset[str]:
    """Words that look like keyphrases but aren't concepts: section names and unit symbols."""
    words = {alias for aliases in SECTION_ALIASES.values() for alias in aliases}
    for unit in load("si_units")["units"]:
        words.add(unit["symbol"].lower())
        words.add(unit["name"].lower())
    return frozenset(words)


def _excluded_index(seg: Segmentation) -> SpanIndex:
    return SpanIndex(
        (p.start, p.end) for p in detect_protected(seg.text) if p.kind in EXCLUDE_KINDS
    )


MAX_TERM_TOKENS = 5


def _expand_compound(seg: Segmentation, s: int, e: int, lo: int, hi: int) -> tuple[int, int]:
    """Grow a keyphrase to its whole noun compound: YAKE often returns fragments such as
    "capacitive soil" or "moisture sensor" of "capacitive soil moisture sensor"."""
    span = seg.doc.char_span(s, e, alignment_mode="expand")
    if span is None:
        return s, e
    first, last = span.start, span.end - 1
    doc = seg.doc
    while (
        last + 1 < len(doc)
        and last - first + 1 < MAX_TERM_TOKENS
        and doc[last].dep_ == "compound"
        and doc[last + 1].pos_ in ("NOUN", "PROPN")
        and doc[last + 1].idx + len(doc[last + 1]) <= hi
    ):
        last += 1
    while (
        first - 1 >= 0
        and last - first + 1 < MAX_TERM_TOKENS
        and doc[first - 1].dep_ in ("compound", "amod")
        and doc[first - 1].pos_ in ("NOUN", "PROPN", "ADJ")
        and first <= doc[first - 1].head.i <= last
        and doc[first - 1].idx >= lo
        and doc[first - 1].lower_ not in GENERIC_MODIFIERS
        and not doc[first - 1].is_stop
    ):
        first -= 1
    return doc[first].idx, doc[last].idx + len(doc[last])


def noun_keyphrases(
    seg: Segmentation, start: int = 0, end: int | None = None, top: int = 10
) -> list[tuple[str, int, int]]:
    """(surface, start, end) of the first occurrence of each good keyphrase in [start, end)."""
    end = len(seg.text) if end is None else end
    region = seg.text[start:end]
    if "terms.style" not in seg.cache:
        seg.cache["terms.style"] = _style_phrase_index(seg)
        seg.cache["terms.excluded"] = _excluded_index(seg)
    style: SpanIndex = seg.cache["terms.style"]
    excluded: SpanIndex = seg.cache["terms.excluded"]
    out: list[tuple[str, int, int]] = []
    seen: set[str] = set()
    candidates = keyphrases(region, top=top * 3)
    # frequent multi-word noun chunks are good terms too
    chunk_counts: Counter[str] = Counter()
    for chunk in seg.doc.noun_chunks:
        if start <= chunk.start_char and chunk.end_char <= end:
            toks = [t for t in chunk if t.pos_ not in ("DET", "PRON") and not t.is_punct]
            if len(toks) >= 2:
                chunk_counts[" ".join(t.text for t in toks).lower()] += 1
    candidates += [c for c, n in chunk_counts.most_common() if n >= 2 and c not in candidates]
    for phrase in candidates:
        low = phrase.lower()
        words = low.split()
        if low in seen or len(low) < 3 or low in _non_terms():
            continue
        if len(words) == 2 and words[0] in GENERIC_MODIFIERS:
            continue  # "significant attention", "major problem": evaluation, not a concept
        if " " not in low and zipf(low) > SINGLE_WORD_MAX_ZIPF:
            continue
        for m in re.finditer(
            rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", region, flags=re.IGNORECASE
        ):
            s, e = start + m.start(), start + m.end()
            if style.overlaps(s, e) or excluded.overlaps(s, e) or not _is_nominal(seg, s, e):
                continue
            s, e = _expand_compound(seg, s, e, start, end)
            if style.overlaps(s, e) or excluded.overlaps(s, e):
                s, e = start + m.start(), start + m.end()
            surface = seg.text[s:e]
            full = surface.lower()
            if any(full in x or x in full for x in seen):
                break
            seen.add(full)
            out.append((surface, s, e))
            break
        if len(out) >= top:
            break
    return out
