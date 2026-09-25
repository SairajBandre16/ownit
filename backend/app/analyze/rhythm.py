"""Rhythm: sentence-length variation ("burstiness"), opener variety, monotone runs."""

from __future__ import annotations

import math
import statistics
from collections import Counter

from spacy.tokens import Span

from app.analyze.base import AnalyzerContext, MetricResult, make_issue
from app.core.explain import explain
from app.core.segment import Sentence

SIMILAR_TOLERANCE = 0.15  # lengths within ±15 % (min ±2 words) count as similar
MIN_RUN = 3


def opener_key(span: Span) -> str:
    """First-token signature: lemma for function words, POS otherwise (so "The motor" and
    "The sensor" share an opener, but "Motors" and "Sensors" don't)."""
    toks = [t for t in span if not (t.is_punct or t.is_space)]
    if not toks:
        return ""
    t = toks[0]
    if t.is_stop or t.pos_ in ("DET", "PRON", "ADP", "CCONJ", "SCONJ", "ADV", "AUX"):
        return t.lower_
    return t.pos_


def opener_word(span: Span) -> str:
    toks = [t for t in span if not (t.is_punct or t.is_space)]
    return toks[0].text if toks else ""


def normalized_entropy(keys: list[str]) -> float:
    if len(keys) < 2:
        return 1.0
    counts = Counter(keys)
    n = len(keys)
    h = -sum((c / n) * math.log(c / n) for c in counts.values())
    return h / math.log(min(n, len(keys))) if n > 1 else 1.0


def similar(a: int, b: int) -> bool:
    tol = max(2.0, SIMILAR_TOLERANCE * max(a, b))
    return abs(a - b) <= tol


def monotone_runs(sents: list[Sentence]) -> list[list[Sentence]]:
    """Maximal runs (≥3) of consecutive sentences in one paragraph with similar lengths."""
    runs: list[list[Sentence]] = []
    cur: list[Sentence] = []
    for s in sents:
        if cur and s.paragraph == cur[-1].paragraph and all(similar(s.words, c.words) for c in cur):
            cur.append(s)
        else:
            if len(cur) >= MIN_RUN:
                runs.append(cur)
            cur = [s]
    if len(cur) >= MIN_RUN:
        runs.append(cur)
    return runs


def analyze(ctx: AnalyzerContext) -> MetricResult:
    sents = ctx.seg.body_sentences
    lengths = [s.words for s in sents]
    issues = []

    sd = statistics.pstdev(lengths) if len(lengths) >= 2 else 8.0
    keys = [opener_key(s.span) for s in sents]
    entropy = normalized_entropy(keys) if len(keys) >= 3 else 1.0

    runs = monotone_runs(sents)
    for run in runs:
        lo, hi = min(s.words for s in run), max(s.words for s in run)
        issues.append(
            make_issue(
                start=run[0].start,
                end=run[-1].end,
                category="rhythm",
                rule="monotone_run",
                severity="info",
                message=explain("issue.monotone_run", n=len(run), lo=lo, hi=hi),
                lesson_slug="sentence-rhythm",
            )
        )

    # 3+ consecutive sentences with the same first word
    i = 0
    while i < len(sents):
        j = i
        w = opener_word(sents[i].span).lower()
        while j + 1 < len(sents) and opener_word(sents[j + 1].span).lower() == w and w:
            j += 1
        if j - i + 1 >= 3:
            issues.append(
                make_issue(
                    start=sents[i].start,
                    end=sents[j].end,
                    category="rhythm",
                    rule="repeated_opener",
                    severity="warn",
                    message=explain(
                        "issue.repeated_opener", n=j - i + 1, word=opener_word(sents[i].span)
                    ),
                    lesson_slug="sentence-openers",
                )
            )
        i = j + 1

    n = max(len(sents), 1)
    return MetricResult(
        name="rhythm",
        metrics={
            "sentence_length_mean": statistics.fmean(lengths) if lengths else 0.0,
            "sentence_length_sd": sd,
            "opener_entropy": entropy,
            "monotone_runs_per_10s": 10.0 * len(runs) / n,
        },
        issues=issues,
    )
