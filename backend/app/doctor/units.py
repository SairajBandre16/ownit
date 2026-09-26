"""Units (CLAUDE.md §9.5): number–unit spacing, unit case, plural unit symbols, SI and
imperial units mixed for one quantity, and numbers without units in Results."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.analyze.base import AnalyzerContext, make_issue
from app.core.explain import explain
from app.core.resources import load
from app.schemas.common import Issue

CATEGORY = "engineering"
LESSON = "units"
NUMBER = r"(?:[±+\-−~≈]\s?)?\d+(?:[.,]\d+)*(?:\s?(?:×|x)\s?10\^?[−\-]?\d+)?"
# symbols written without a space by convention
NO_SPACE = {"%", "°", "′", "″", "‰"}
# unit symbols that are also English words
WORD_UNITS = {"in", "at", "a", "am", "pm", "mi", "yd", "ha", "t"}
RESULT_SECTIONS = {"results", "discussion"}
# a number after one of these words is dimensionless ("the COP was 2.4")
DIMENSIONLESS = {
    "ratio",
    "coefficient",
    "factor",
    "cop",
    "index",
    "number",
    "gain",
    "ph",
    "mach",
    "grade",
    "score",
    "class",
    "rank",
    "times",
    "fold",
    "trial",
    "trials",
    "sample",
    "samples",
    "run",
    "runs",
    "test",
    "tests",
    "step",
    "steps",
    "level",
    "version",
    "stage",
    "phase",
    "cycle",
    "cycles",
    "specimen",
    "specimens",
}
# "3 out of 8", "5 of the 8", "20 x 30" (a count or dimension follows)
COUNT_WORDS_AFTER = {"of", "out", "x", "×", "by"}
# "120 to 410 Pa", "3 and 4 V": a range, the unit comes after the second number
RANGE_WORDS = {"to", "and", "or", "–", "-"}


@dataclass(frozen=True)
class UnitInfo:
    symbol: str
    quantity: str
    system: str  # "SI" | "imperial" | "other"


@lru_cache(maxsize=1)
def catalogue() -> dict[str, Any]:
    data = load("si_units")
    units = {u["symbol"]: UnitInfo(u["symbol"], u["quantity"], u["system"]) for u in data["units"]}
    return {"units": units, "miscased": data["miscased"], "plurals": data["plurals"]}


@lru_cache(maxsize=1)
def unit_regex() -> re.Pattern[str]:
    c = catalogue()
    symbols = set(c["units"]) | set(c["miscased"]) | set(c["plurals"])
    alts = "|".join(re.escape(s) for s in sorted(symbols, key=len, reverse=True))
    # the unit must end the token: "5 m" but not "5 months"
    return re.compile(rf"(?<![\w.])(?P<num>{NUMBER})(?P<space>\s?)(?P<unit>{alts})(?![A-Za-z0-9])")


@dataclass(frozen=True)
class Quantity:
    start: int
    end: int
    number: str
    space: str
    unit: str


def find_quantities(text: str) -> list[Quantity]:
    out = []
    for m in unit_regex().finditer(text):
        unit = m.group("unit")
        # "45 in the test" is a preposition, not inches
        if unit in WORD_UNITS and re.match(r"\s+[a-z]", text[m.end() :]):
            continue
        out.append(Quantity(m.start(), m.end(), m.group("num"), m.group("space"), unit))
    return out


def _issue(
    q: Quantity, rule: str, key: str, suggestion: str | None, severity: str = "warn", **fmt: str
) -> Issue:
    return make_issue(
        start=q.start,
        end=q.end,
        category=CATEGORY,
        rule=rule,
        severity=severity,  # type: ignore[arg-type]
        message=explain(key, **fmt),
        suggestion=suggestion,
        lesson_slug=LESSON,
    )


def check(ctx: AnalyzerContext) -> list[Issue]:
    text = ctx.seg.text
    c = catalogue()
    issues: list[Issue] = []
    systems: dict[str, dict[str, Quantity]] = defaultdict(dict)  # quantity -> system -> first use
    for q in find_quantities(text):
        if ctx.hard_index.overlaps(q.start, q.end):
            continue
        fixed_unit = q.unit
        if q.unit in c["plurals"]:
            fixed_unit = c["plurals"][q.unit]
            issues.append(
                _issue(
                    q,
                    "units.plural",
                    "issue.unit_plural",
                    f"{q.number} {fixed_unit}",
                    bad=q.unit,
                    fix=fixed_unit,
                )
            )
        elif q.unit in c["miscased"] and q.unit not in c["units"]:
            fix = c["miscased"][q.unit]
            if fix is None:
                continue  # ambiguous ("MW" vs "mW"): don't guess
            fixed_unit = fix
            issues.append(
                _issue(q, "units.case", "issue.unit_case", f"{q.number} {fix}", bad=q.unit, fix=fix)
            )
        elif not q.space and q.unit not in NO_SPACE and not q.unit.startswith("°"):
            fix = f"{q.number} {q.unit}"
            issues.append(_issue(q, "units.spacing", "issue.unit_spacing", fix, fix=fix))
        info = c["units"].get(fixed_unit)
        if info is not None:
            group = "SI" if info.system == "SI" else "non-SI"
            systems[info.quantity].setdefault(group, q)
    for quantity, used in systems.items():
        if len(used) > 1:
            q = used["non-SI"]
            issues.append(
                _issue(
                    q,
                    "units.mixed",
                    "issue.unit_mixed",
                    None,
                    severity="info",
                    systems="SI and non-SI",
                    quantity=quantity,
                )
            )
    issues += _numbers_without_units(ctx)
    return issues


def _numbers_without_units(ctx: AnalyzerContext) -> list[Issue]:
    """Results/Discussion numbers that measure something but have no unit."""
    text = ctx.seg.text
    with_unit = [(q.start, q.end) for q in find_quantities(text)]
    issues: list[Issue] = []
    for s in ctx.seg.body_sentences:
        if s.section not in RESULT_SECTIONS:
            continue
        toks = list(s.span)
        for k, t in enumerate(toks):
            if not re.fullmatch(r"\d+(?:\.\d+)?", t.text):
                continue
            a, b = t.idx, t.idx + len(t.text)
            if any(x <= a < y for x, y in with_unit) or (
                ctx.all_index.overlaps(a, b) and _protected_ref(ctx, a, b)
            ):
                continue
            if 1900 <= float(t.text) <= 2100 and "." not in t.text:
                continue  # a year
            nxt = toks[k + 1] if k + 1 < len(toks) else None
            prev = [x.lower_ for x in toks[max(0, k - 6) : k]]
            if nxt is not None and (
                nxt.pos_ in ("NOUN", "PROPN")
                or nxt.lower_ in COUNT_WORDS_AFTER
                or nxt.text == "%"
                or (
                    nxt.lower_ in RANGE_WORDS
                    and k + 2 < len(toks)
                    and any(x <= toks[k + 2].idx < y for x, y in with_unit)
                )
            ):
                continue  # "5 samples", "3 out of 8", "120 to 410 Pa"
            if any(p in DIMENSIONLESS for p in prev):
                continue
            if t.dep_ == "nummod" or (
                k > 0 and toks[k - 1].lower_ in ("fig", "figure", "table", "eq", "no")
            ):
                continue
            issues.append(
                make_issue(
                    start=a,
                    end=b,
                    category=CATEGORY,
                    rule="units.missing",
                    severity="info",
                    message=explain("issue.number_no_unit", section=s.section.capitalize()),
                    lesson_slug=LESSON,
                )
            )
    return issues


def _protected_ref(ctx: AnalyzerContext, a: int, b: int) -> bool:
    return any(
        p.start <= a and b <= p.end and p.kind in ("reference", "citation", "equation", "code")
        for p in ctx.protected
    )
