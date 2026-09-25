"""Shared analyzer types: metric results, issue construction, band scoring."""

from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import orjson

from app.core.protect import Protected, detect_protected
from app.core.segment import Segmentation
from app.core.spans import SpanIndex
from app.schemas.common import Issue, Severity

BANDS_PATH = Path(__file__).with_name("bands.json")

# issues from lexicons are suppressed inside these protected kinds
HARD_PROTECTED = {"quote", "code", "equation", "citation", "url"}


@lru_cache(maxsize=1)
def bands() -> dict[str, Any]:
    return orjson.loads(BANDS_PATH.read_bytes())  # type: ignore[no-any-return]


def band_score(value: float, points: list[list[float]]) -> float:
    """Piecewise-linear interpolation of `value` through [(x, score), ...] (x ascending)."""
    if value <= points[0][0]:
        return float(points[0][1])
    for (x0, y0), (x1, y1) in itertools.pairwise(points):
        if value <= x1:
            t = (value - x0) / (x1 - x0) if x1 != x0 else 1.0
            return float(y0 + t * (y1 - y0))
    return float(points[-1][1])


@dataclass
class AnalyzerContext:
    seg: Segmentation
    protected: list[Protected]
    target_grade: float = 12.0
    hard_index: SpanIndex = field(init=False)
    all_index: SpanIndex = field(init=False)

    def __post_init__(self) -> None:
        self.hard_index = SpanIndex(
            (p.start, p.end) for p in self.protected if p.kind in HARD_PROTECTED
        )
        self.all_index = SpanIndex((p.start, p.end) for p in self.protected)

    @classmethod
    def build(cls, seg: Segmentation, target_grade: float | None = None) -> AnalyzerContext:
        tg = target_grade if target_grade is not None else float(bands()["default_target_grade"])
        return cls(seg=seg, protected=detect_protected(seg.text), target_grade=tg)

    @property
    def body_words(self) -> int:
        return sum(s.words for s in self.seg.body_sentences)

    def per_100w(self, count: float) -> float:
        return 100.0 * count / max(self.body_words, 1)

    def in_body(self, start: int) -> bool:
        """Offset lies in a body sentence (not a heading or reference list)."""
        return any(s.start <= start < s.end for s in self.seg.body_sentences)


@dataclass
class MetricResult:
    name: str  # sub-score name
    metrics: dict[str, float]
    issues: list[Issue] = field(default_factory=list)
    available: bool = True


def issue_id(rule: str, start: int, end: int) -> str:
    return hashlib.sha1(f"{rule}:{start}:{end}".encode()).hexdigest()[:10]


def make_issue(
    *,
    start: int,
    end: int,
    category: str,
    rule: str,
    severity: Severity,
    message: str,
    suggestion: str | None = None,
    lesson_slug: str | None = None,
) -> Issue:
    return Issue(
        id=issue_id(rule, start, end),
        start=start,
        end=end,
        category=category,
        rule=rule,
        severity=severity,
        message=message,
        suggestion=suggestion,
        lesson_slug=lesson_slug,
    )


def score_subscore(result: MetricResult) -> tuple[float | None, dict[str, dict[str, float]]]:
    """Map a result's metrics through its bands. Returns (score, per-metric detail)."""
    spec = bands()["subscores"][result.name]
    if not result.available:
        return None, {}
    detail: dict[str, dict[str, float]] = {}
    total = weight_sum = 0.0
    for metric, cfg in spec.items():
        if metric not in result.metrics:
            continue
        value = result.metrics[metric]
        s = band_score(value, cfg["band"])
        detail[metric] = {"value": round(value, 3), "score": round(s, 1)}
        total += s * cfg["weight"]
        weight_sum += cfg["weight"]
    if weight_sum == 0:
        return None, detail
    return round(total / weight_sum, 1), detail
