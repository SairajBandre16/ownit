"""Engineering Report Doctor (CLAUDE.md §9.5, U4): runs every check and de-duplicates."""

from __future__ import annotations

from collections import Counter

from app.analyze.base import AnalyzerContext
from app.core.segment import segment
from app.doctor import abbreviations, claims, figures, structure, tense, units
from app.schemas.common import Issue

RULE_GROUP = {"abbr": "abbreviations"}
CHECKS = {
    "units": units.check,
    "abbreviations": abbreviations.check,
    "figures": figures.check,
    "tense": tense.check,
    "claims": claims.check,
    "structure": structure.check,
}


def run_doctor(text: str) -> tuple[list[Issue], dict[str, int]]:
    ctx = AnalyzerContext.build(segment(text))
    issues: list[Issue] = []
    seen: set[str] = set()
    for check in CHECKS.values():
        for i in check(ctx):
            if i.id not in seen:
                seen.add(i.id)
                issues.append(i)
    issues.sort(key=lambda i: (i.start, i.end))
    # rule prefixes are the check names, except "abbr." for abbreviations
    counts = Counter(RULE_GROUP.get(p, p) for p in (i.rule.split(".")[0] for i in issues))
    return issues, {name: counts.get(name, 0) for name in CHECKS}
