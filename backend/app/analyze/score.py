"""Run all §5 analyzers and combine them into the writing score."""

from __future__ import annotations

from dataclasses import dataclass

from app.analyze import clarity, correctness, rhythm, vocabulary, voice
from app.analyze.base import AnalyzerContext, MetricResult, bands, score_subscore
from app.core.segment import segment
from app.schemas.common import Issue

ANALYZERS = (clarity, rhythm, vocabulary, voice, correctness)
# when two issues cover exactly the same span, keep the more specific rule
RULE_PRIORITY = [
    "ai_style_phrase",
    "weak_verb",
    "nominalization",
    "wordy_phrase",
    "cliche",
    "filler",
    "stacked_hedge",
    "hedge",
]


@dataclass
class AnalysisResult:
    score: float
    subscores: dict[str, float | None]
    details: dict[str, dict[str, dict[str, float]]]
    metrics: dict[str, dict[str, float]]
    issues: list[Issue]
    words: int
    sentence_lengths: list[int]
    ctx: AnalyzerContext


def dedupe(issues: list[Issue]) -> list[Issue]:
    prio = {r: i for i, r in enumerate(RULE_PRIORITY)}
    best: dict[tuple[int, int], Issue] = {}
    out: list[Issue] = []
    for iss in issues:
        if iss.rule not in prio:
            out.append(iss)
            continue
        key = (iss.start, iss.end)
        cur = best.get(key)
        if cur is None or prio[iss.rule] < prio[cur.rule]:
            best[key] = iss
    out.extend(best.values())
    # drop a lexicon issue fully inside a higher-priority lexicon issue
    lex = sorted((i for i in out if i.rule in prio), key=lambda i: (i.start, -(i.end - i.start)))
    kept: list[Issue] = []
    for iss in lex:
        if any(
            k.start <= iss.start and iss.end <= k.end and prio[k.rule] <= prio[iss.rule]
            for k in kept
        ):
            continue
        kept.append(iss)
    others = [i for i in out if i.rule not in prio]
    return sorted(others + kept, key=lambda i: (i.start, i.end, i.rule))


def overall(subscores: dict[str, float | None]) -> float:
    weights = bands()["overall_weights"]
    total = wsum = 0.0
    for name, s in subscores.items():
        if s is None:
            continue
        total += s * weights[name]
        wsum += weights[name]
    return round(total / wsum, 1) if wsum else 0.0


def run_analysis(text: str, target_grade: float | None = None) -> AnalysisResult:
    seg = segment(text)
    ctx = AnalyzerContext.build(seg, target_grade)
    results: list[MetricResult] = [a.analyze(ctx) for a in ANALYZERS]
    subscores: dict[str, float | None] = {}
    details: dict[str, dict[str, dict[str, float]]] = {}
    issues: list[Issue] = []
    for r in results:
        s, d = score_subscore(r)
        subscores[r.name] = s
        details[r.name] = d
        issues.extend(r.issues)
    return AnalysisResult(
        score=overall(subscores),
        subscores=subscores,
        details=details,
        metrics={r.name: r.metrics for r in results},
        issues=dedupe(issues),
        words=ctx.body_words,
        sentence_lengths=[s.words for s in seg.body_sentences],
        ctx=ctx,
    )


def quick_score(text: str) -> float:
    """Overall score only (used for before/after in /humanize)."""
    return run_analysis(text).score
