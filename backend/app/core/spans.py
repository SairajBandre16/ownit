"""Character-offset utilities. All spans are half-open [start, end)."""

from __future__ import annotations

import bisect
import difflib
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class CharSpan:
    start: int
    end: int

    def __len__(self) -> int:
        return self.end - self.start

    def overlaps(self, start: int, end: int) -> bool:
        return overlaps(self.start, self.end, start, end)


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """True if [a_start, a_end) and [b_start, b_end) share at least one character."""
    return a_start < b_end and b_start < a_end


def merge_spans(spans: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or touching spans into a sorted, disjoint list."""
    out: list[list[int]] = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return [(s, e) for s, e in out]


class SpanIndex:
    """Fast overlap queries over a set of spans (merged internally)."""

    def __init__(self, spans: Iterable[tuple[int, int]]) -> None:
        merged = merge_spans(spans)
        self._starts = [s for s, _ in merged]
        self._ends = [e for _, e in merged]

    def __len__(self) -> int:
        return len(self._starts)

    def overlaps(self, start: int, end: int) -> bool:
        if end <= start:
            # empty span: treat as a position; "inside" a span counts
            i = bisect.bisect_right(self._starts, start) - 1
            return i >= 0 and self._starts[i] < start < self._ends[i]
        i = bisect.bisect_left(self._ends, start + 1)
        return i < len(self._starts) and self._starts[i] < end

    def spans_in(self, start: int, end: int) -> list[tuple[int, int]]:
        """Spans overlapping [start, end), clipped to it."""
        i = bisect.bisect_left(self._ends, start + 1)
        out = []
        while i < len(self._starts) and self._starts[i] < end:
            out.append((max(self._starts[i], start), min(self._ends[i], end)))
            i += 1
        return out

    def covered(self, start: int, end: int) -> bool:
        """True if [start, end) lies entirely inside one span."""
        i = bisect.bisect_right(self._starts, start) - 1
        return i >= 0 and self._ends[i] >= end


def shift_spans(spans: Sequence[tuple[int, int]], offset: int) -> list[tuple[int, int]]:
    return [(s + offset, e + offset) for s, e in spans]


@dataclass(frozen=True)
class Edit:
    """Replace text[start:end] with `replacement`."""

    start: int
    end: int
    replacement: str


def apply_edits(text: str, edits: Iterable[Edit]) -> str:
    """Apply non-overlapping edits (any order) to `text`."""
    ordered = sorted(edits, key=lambda e: (e.start, e.end))
    parts: list[str] = []
    pos = 0
    for e in ordered:
        if e.start < pos:
            raise ValueError(f"overlapping edit at {e.start}")
        parts.append(text[pos : e.start])
        parts.append(e.replacement)
        pos = e.end
    parts.append(text[pos:])
    return "".join(parts)


_TOKEN_RE = re.compile(r"\w+(?:['’]\w+)*|[^\w\s]|\s+")


@dataclass(frozen=True)
class DiffHunk:
    orig_start: int
    orig_end: int
    new_start: int
    new_end: int
    original: str
    replacement: str


def diff_hunks(a: str, b: str) -> list[DiffHunk]:
    """Word-level diff of two strings as character-offset hunks.

    Hunks are expanded to whole words; whitespace-only differences at the hunk edges are
    trimmed so reasons read naturally ("utilize" -> "use", not " utilize" -> " use").
    """
    ta = _TOKEN_RE.findall(a)
    tb = _TOKEN_RE.findall(b)
    oa = _offsets(ta)
    ob = _offsets(tb)
    hunks: list[DiffHunk] = []
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        a_s, a_e = oa[i1], oa[i2]
        b_s, b_e = ob[j1], ob[j2]
        hunks.append(DiffHunk(a_s, a_e, b_s, b_e, a[a_s:a_e], b[b_s:b_e]))
    return _merge_close(hunks, a, b)


def _offsets(tokens: list[str]) -> list[int]:
    out = [0]
    for t in tokens:
        out.append(out[-1] + len(t))
    return out


def _merge_close(hunks: list[DiffHunk], a: str, b: str) -> list[DiffHunk]:
    """Merge hunks separated only by whitespace so one rewrite = one hunk."""
    merged: list[DiffHunk] = []
    for h in hunks:
        if merged:
            p = merged[-1]
            gap_a = a[p.orig_end : h.orig_start]
            gap_b = b[p.new_end : h.new_start]
            if gap_a.strip() == "" and gap_b.strip() == "" and len(gap_a) <= 1:
                merged[-1] = DiffHunk(
                    p.orig_start,
                    h.orig_end,
                    p.new_start,
                    h.new_end,
                    a[p.orig_start : h.orig_end],
                    b[p.new_start : h.new_end],
                )
                continue
        merged.append(h)
    return merged
