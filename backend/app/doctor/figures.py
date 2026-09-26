"""Figures and tables (CLAUDE.md §9.5): every captioned figure/table is referred to in the
text, first mentions come in number order, and references point at an existing caption.

Captions are lines that start with "Figure 3:", "Fig. 3.", "Table 2 –" etc. (plain text or
paragraphs from a .docx). "Referenced but no caption" is only reported when the document has
captions for that kind at all; pasted text often has none.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass

from app.analyze.base import AnalyzerContext, make_issue
from app.core.explain import explain
from app.schemas.common import Issue

CATEGORY = "engineering"
LESSON = "figures-and-tables"
KIND_OF = {
    "fig": "Figure",
    "figure": "Figure",
    "figs": "Figure",
    "figures": "Figure",
    "table": "Table",
    "tables": "Table",
    "tab": "Table",
}
MENTION_RE = re.compile(
    r"\b(Figs?\.|Figures?|Tables?|Tab\.)\s*(\d+)(?:\s*\(?[a-z]\))?"
    r"(?:\s*(?:–|-|to|and|&|,)\s*(\d+))?",
    re.IGNORECASE,
)
LINE_RE = re.compile(r"[^\n]+")
CAPTION_RE = re.compile(r"^\s*(Fig\.|Figure|Table)\s*(\d+)\s*[.:–—-]", re.IGNORECASE)


@dataclass(frozen=True)
class Ref:
    kind: str  # "Figure" | "Table"
    number: int
    start: int
    end: int


def _kind(word: str) -> str:
    return KIND_OF[word.lower().rstrip(".")]


def captions(ctx: AnalyzerContext) -> list[Ref]:
    """Caption lines (a paragraph may hold several consecutive captions)."""
    out = []
    for line in LINE_RE.finditer(ctx.seg.text):
        m = CAPTION_RE.match(line.group())
        if m:
            out.append(Ref(_kind(m.group(1)), int(m.group(2)), line.start(), line.end()))
    return out


def mentions(ctx: AnalyzerContext, caption_spans: list[tuple[int, int]]) -> list[Ref]:
    """References in the running text (not in captions), ranges expanded ("Figs. 3–5")."""
    out = []
    for m in MENTION_RE.finditer(ctx.seg.text):
        if any(s <= m.start() < e for s, e in caption_spans):
            continue
        kind = _kind(m.group(1))
        first = int(m.group(2))
        last = int(m.group(3)) if m.group(3) else first
        is_range = m.group(3) and re.search(r"–|-|to", m.group(0)[len(m.group(1)) :])
        numbers = range(first, last + 1) if is_range and 0 < last - first < 20 else {first, last}
        for n in sorted(numbers):
            out.append(Ref(kind, n, m.start(), m.end()))
    return out


def check(ctx: AnalyzerContext) -> list[Issue]:
    caps = captions(ctx)
    refs = mentions(ctx, [(c.start, c.end) for c in caps])
    issues: list[Issue] = []

    def issue(ref: Ref, rule: str, key: str, severity: str, **fmt: object) -> None:
        issues.append(
            make_issue(
                start=ref.start,
                end=ref.end,
                category=CATEGORY,
                rule=rule,
                severity=severity,  # type: ignore[arg-type]
                message=explain(key, **fmt),
                lesson_slug=LESSON,
            )
        )

    for kind in ("Figure", "Table"):
        kind_refs = [r for r in refs if r.kind == kind]
        kind_caps = [c for c in caps if c.kind == kind]
        mentioned = {r.number for r in kind_refs}
        # first mentions should run 1, 2, 3 …
        seen: list[int] = []
        for r in kind_refs:
            if r.number in seen:
                continue
            # the n-th figure introduced should be Figure n
            if r.number > len(seen) + 1 and (r.number - 1) not in seen:
                issue(
                    r,
                    "figures.order",
                    "issue.figure_order",
                    "info",
                    kind=kind,
                    n=r.number,
                    prev=r.number - 1,
                    kind_lower=kind.lower(),
                )
            seen.append(r.number)
        for c in kind_caps:
            if c.number not in mentioned:
                issue(
                    c,
                    "figures.unreferenced",
                    "issue.figure_unreferenced",
                    "warn",
                    kind=kind,
                    n=c.number,
                )
        if kind_caps:
            captioned = {c.number for c in kind_caps}
            reported: set[int] = set()
            for r in kind_refs:
                if r.number not in captioned and r.number not in reported:
                    reported.add(r.number)
                    issue(
                        r, "figures.missing", "issue.figure_missing", "warn", kind=kind, n=r.number
                    )
            numbers = sorted(captioned)
            for a, b in itertools.pairwise(numbers):
                if b != a + 1:
                    c = next(x for x in kind_caps if x.number == b)
                    issue(
                        c,
                        "figures.order",
                        "issue.caption_gap",
                        "info",
                        kind=kind,
                        n=b,
                        prev=a,
                        kind_lower=kind.lower(),
                    )
    return issues
