"""Key technical terms: YAKE keyphrases filtered to real noun phrases.

A keyphrase counts only if its occurrence in the parsed text is a noun phrase (last token a
noun, the rest nouns/adjectives/numbers or "of"), it isn't part of a stock or wordy phrase
("plays a crucial role"), and it isn't inside maths, code, citations or URLs.
"""

from __future__ import annotations

import re
from collections import Counter

from app.core.nlp import zipf
from app.core.protect import _is_nominal, _style_phrase_index, detect_protected, keyphrases
from app.core.segment import Segmentation
from app.core.spans import SpanIndex

EXCLUDE_KINDS = {"equation", "code", "citation", "url", "number", "quote", "reference"}
SINGLE_WORD_MAX_ZIPF = 4.7  # "motor", "torque" are terms; "results", "students" are not


def _excluded_index(seg: Segmentation) -> SpanIndex:
    return SpanIndex(
        (p.start, p.end) for p in detect_protected(seg.text) if p.kind in EXCLUDE_KINDS
    )


def noun_keyphrases(
    seg: Segmentation, start: int = 0, end: int | None = None, top: int = 10
) -> list[tuple[str, int, int]]:
    """(surface, start, end) of the first occurrence of each good keyphrase in [start, end)."""
    end = len(seg.text) if end is None else end
    region = seg.text[start:end]
    style = _style_phrase_index(seg)
    excluded = _excluded_index(seg)
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
        if low in seen or len(low) < 3:
            continue
        if " " not in low and zipf(low) > SINGLE_WORD_MAX_ZIPF:
            continue
        for m in re.finditer(
            rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", region, flags=re.IGNORECASE
        ):
            s, e = start + m.start(), start + m.end()
            if style.overlaps(s, e) or excluded.overlaps(s, e) or not _is_nominal(seg, s, e):
                continue
            if any(low in x or x in low for x in seen):
                break
            seen.add(low)
            out.append((m.group(), s, e))
            break
        if len(out) >= top:
            break
    return out
