"""Correctness: LanguageTool matches per 100 words, weighted by category."""

from __future__ import annotations

from app.analyze.base import AnalyzerContext, MetricResult, make_issue
from app.core.explain import explain
from app.core.nlp import get_languagetool
from app.schemas.common import Severity

CATEGORY_WEIGHT = {
    "TYPOS": 1.0,
    "GRAMMAR": 1.0,
    "PUNCTUATION": 0.7,
    "CASING": 0.7,
    "CONFUSED_WORDS": 1.0,
    "STYLE": 0.4,
    "REDUNDANCY": 0.4,
    "TYPOGRAPHY": 0.3,
}
SEVERITY: dict[str, Severity] = {
    "TYPOS": "error",
    "GRAMMAR": "error",
    "CONFUSED_WORDS": "error",
    "PUNCTUATION": "warn",
    "CASING": "warn",
}
LESSON = {"TYPOS": "spelling", "PUNCTUATION": "punctuation"}
# protected kinds where spelling "errors" are expected (abbreviations, names, code, maths)
SKIP_IN = {
    "abbreviation",
    "entity",
    "code",
    "equation",
    "number",
    "url",
    "citation",
    "term",
    "keep",
}


def analyze(ctx: AnalyzerContext) -> MetricResult:
    lt = get_languagetool()
    if not lt.available():
        return MetricResult(name="correctness", metrics={}, available=False)
    text = ctx.seg.text
    matches = lt.check(text)
    issues = []
    weighted = 0.0
    for m in matches:
        if m.category == "TYPOS" and any(
            p.kind in SKIP_IN and p.start <= m.start and m.end <= p.end for p in ctx.protected
        ):
            continue
        if not ctx.in_body(m.start):
            continue
        weighted += CATEGORY_WEIGHT.get(m.category, 0.5)
        issues.append(
            make_issue(
                start=m.start,
                end=m.end,
                category="correctness",
                rule=f"lt:{m.rule_id}",
                severity=SEVERITY.get(m.category, "info"),
                message=explain("issue.grammar", message=m.message),
                suggestion=m.replacements[0] if m.replacements else None,
                lesson_slug=LESSON.get(m.category, "grammar"),
            )
        )
    return MetricResult(
        name="correctness",
        metrics={"lt_errors_per_100w": ctx.per_100w(weighted), "lt_matches": float(len(issues))},
        issues=issues,
    )
