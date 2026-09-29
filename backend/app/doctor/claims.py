"""Claim–evidence check (CLAUDE.md §9.5): a strong claim ("proves", "clearly shows",
"significantly", "always", "the best" …) with no citation, number or figure/table reference in
the same or the next sentence → "Unsupported claim. Add evidence or soften it"."""

from __future__ import annotations

import re
from functools import lru_cache

from app.analyze.base import AnalyzerContext, make_issue
from app.core.explain import explain
from app.core.lexicon import PhraseLexicon
from app.core.resources import load
from app.schemas.common import Issue

CATEGORY = "engineering"
LESSON = "citing-claims"
EVIDENCE_KINDS = {"citation", "number", "reference"}
DIGIT_RE = re.compile(r"\d")
SKIP_SECTIONS = {"references", "appendix", "acknowledgements"}


@lru_cache(maxsize=1)
def markers() -> PhraseLexicon:
    return PhraseLexicon({m.lower(): None for m in load("claim_markers")["markers"]})


def check(ctx: AnalyzerContext) -> list[Issue]:
    evidence = [(p.start, p.end) for p in ctx.protected if p.kind in EVIDENCE_KINDS]

    def has_evidence(start: int, end: int, text: str) -> bool:
        return bool(DIGIT_RE.search(text)) or any(s < end and start < e for s, e in evidence)

    sents = ctx.seg.body_sentences
    issues: list[Issue] = []
    for i, s in enumerate(sents):
        if s.section in SKIP_SECTIONS:
            continue
        hits = [
            m
            for m in markers().find(s.text)
            if not ctx.hard_index.overlaps(s.start + m.start, s.start + m.end)
        ]
        if not hits:
            continue
        nxt = sents[i + 1] if i + 1 < len(sents) and sents[i + 1].paragraph == s.paragraph else None
        if has_evidence(s.start, s.end, s.text) or (
            nxt is not None and has_evidence(nxt.start, nxt.end, nxt.text)
        ):
            continue
        m = hits[0]
        issues.append(
            make_issue(
                start=s.start + m.start,
                end=s.start + m.end,
                category=CATEGORY,
                rule="claims.unsupported",
                severity="warn",
                message=explain("issue.unsupported_claim", marker=m.text),
                lesson_slug=LESSON,
            )
        )
    return issues
