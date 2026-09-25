"""Simplified version of each paragraph.

Runs the humanize engine once over the whole text at maximum intensity in a neutral tone (so
every simplification passes the same meaning/grammar/fluency gates), then maps each
paragraph's span into the rewritten text using the change offsets.
"""

from __future__ import annotations

import re

import textstat

from app.humanize.pipeline import ChangeRecord, humanize

PARENS_RE = re.compile(r"\s*\((?![^)]*\d{4})[^)]{1,80}\)")  # drop asides, keep citations


def map_offset(pos: int, changes: list[ChangeRecord], side: str = "start") -> int:
    """Map an offset in the original text to the rewritten text."""
    delta = 0
    for c in changes:
        if c.orig_end <= pos and not (side == "start" and c.orig_start == pos):
            delta += (c.new_end - c.new_start) - (c.orig_end - c.orig_start)
        elif c.orig_start < pos < c.orig_end:
            return c.new_end if side == "end" else c.new_start
    return pos + delta


def simplify_paragraphs(text: str, spans: list[tuple[int, int]]) -> list[tuple[str, float, float]]:
    """(simplified text, FK grade before, FK grade after) for each paragraph span."""
    out = humanize(text, tone="neutral", intensity=5, prefer="simplest")
    changes = sorted(out.changes, key=lambda c: c.orig_start)
    results = []
    for start, end in spans:
        ns, ne = map_offset(start, changes, "start"), map_offset(end, changes, "end")
        simple = out.text[ns:ne].strip()
        simple = PARENS_RE.sub("", simple)
        original = text[start:end]
        results.append(
            (
                simple,
                float(textstat.flesch_kincaid_grade(original)),
                float(textstat.flesch_kincaid_grade(simple)),
            )
        )
    return results
