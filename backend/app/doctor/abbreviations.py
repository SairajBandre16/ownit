"""Abbreviations (CLAUDE.md §9.5): used before being defined as "Full Name (ABBR)", defined
twice, or defined but never used.

A definition is "Full Name (ABBR)" or "ABBR (Full Name)" where the initials match. An
abbreviation defined in the Abstract may be defined again in the body (a common convention).
Very common abbreviations (USB, LED, DC …) and unit symbols never need a definition.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.analyze.base import AnalyzerContext, make_issue
from app.core.explain import explain
from app.core.resources import load
from app.schemas.common import Issue
from app.walkthrough.glossary import ABBR_DEF_RE, expansion_for

CATEGORY = "engineering"
LESSON = "abbreviations"
USE_RE = re.compile(r"(?<![\w-])([A-Z][A-Za-z]*[A-Z][A-Za-z]*s?)(?![\w-])")
REVERSE_DEF_RE = re.compile(
    r"(?<![\w-])([A-Z][A-Za-z]*[A-Z][A-Za-z]*)\s+\(([A-Za-z][A-Za-z\s-]{3,80})\)"
)
COMMON = {
    "USB",
    "PC",
    "TV",
    "UK",
    "USA",
    "US",
    "EU",
    "UN",
    "OK",
    "AM",
    "PM",
    "ID",
    "PDF",
    "CD",
    "DVD",
    "GPS",
    "LED",
    "LCD",
    "URL",
    "CPU",
    "RAM",
    "ROM",
    "AC",
    "DC",
    "IEEE",
    "ISO",
    "NASA",
    "AI",
    "IT",
    "HR",
    "CEO",
    "DIY",
    "FAQ",
    "PhD",
    "BSc",
    "MSc",
    "BTech",
    "MTech",
    "BE",
    "ME",
}
# software and product names written in capitals
TOOLS = {
    "LabVIEW",
    "AutoCAD",
    "MATLAB",
    "ANSYS",
    "ABAQUS",
    "COMSOL",
    "SPSS",
    "SCILAB",
    "CATIA",
    "NX",
    "PSPICE",
    "LTSPICE",
}
ROMAN = re.compile(r"^(?:I{1,3}|IV|V|VI{1,3}|IX|X{1,3})$")
SKIP_SECTIONS = {"references", "appendix", "acknowledgements"}


@dataclass(frozen=True)
class Definition:
    abbr: str
    full: str
    start: int  # the whole "Full Name (ABBR)"
    end: int
    abbr_start: int  # the ABBR inside it
    abbr_end: int
    section: str


@lru_cache(maxsize=1)
def _units() -> frozenset[str]:
    return frozenset(u["symbol"] for u in load("si_units")["units"])


@lru_cache(maxsize=1)
def _known() -> dict[str, str]:
    return {k: v for k, v in load("eng_abbreviations").items() if not k.startswith("_")}


def definitions(ctx: AnalyzerContext) -> list[Definition]:
    text = ctx.seg.text
    out: list[Definition] = []
    for m in ABBR_DEF_RE.finditer(text):
        abbr = m.group(2)
        full = expansion_for(m.group(1).split(), abbr)
        if full:
            start = m.end(1) - len(full)
            a0 = m.start(2)
            out.append(
                Definition(
                    abbr, full, start, m.end(), a0, a0 + len(abbr), ctx.seg.section_at(start)
                )
            )
    for m in REVERSE_DEF_RE.finditer(text):
        abbr, full = m.group(1), m.group(2).strip()
        if expansion_for(full.split(), abbr) == full:
            out.append(
                Definition(
                    abbr,
                    full,
                    m.start(),
                    m.end(),
                    m.start(1),
                    m.end(1),
                    ctx.seg.section_at(m.start()),
                )
            )
    return sorted(out, key=lambda d: d.start)


def _needs_definition(abbr: str) -> bool:
    upper = sum(c.isupper() for c in abbr)
    if upper < len(abbr) - upper:
        return False  # "SolidWorks", "LabVIEW": names, not abbreviations
    return not (
        abbr in COMMON or abbr in TOOLS or abbr in _units() or ROMAN.match(abbr) or len(abbr) > 8
    )


def check(ctx: AnalyzerContext) -> list[Issue]:
    text = ctx.seg.text
    defs = definitions(ctx)
    inside_def = [(d.start, d.end) for d in defs]
    headings = [(p.start, p.end) for p in ctx.seg.paragraphs if p.is_heading]

    uses: dict[str, list[tuple[int, int]]] = {}
    for m in USE_RE.finditer(text):
        a, b = m.start(1), m.end(1)
        word = m.group(1)
        abbr = word[:-1] if word.endswith("s") and word[:-1].isupper() else word  # "PLCs"
        if any(s <= a < e for s, e in inside_def) or any(s <= a < e for s, e in headings):
            continue
        if ctx.hard_index.overlaps(a, b) or ctx.seg.section_at(a) in SKIP_SECTIONS:
            continue
        if not _needs_definition(abbr) or not ctx.in_body(a):
            continue
        uses.setdefault(abbr, []).append((a, b))

    by_abbr: dict[str, list[Definition]] = {}
    for d in defs:
        by_abbr.setdefault(d.abbr, []).append(d)

    issues: list[Issue] = []
    for abbr, occ in uses.items():
        first_def = by_abbr.get(abbr, [None])[0]
        a, b = occ[0]
        if first_def is None or a < first_def.start:
            full = first_def.full if first_def else _known().get(abbr)
            issues.append(
                make_issue(
                    start=a,
                    end=b,
                    category=CATEGORY,
                    rule="abbr.undefined",
                    severity="warn",
                    message=explain("issue.abbr_undefined", abbr=abbr),
                    suggestion=f"{full} ({abbr})" if full else None,
                    lesson_slug=LESSON,
                )
            )
    for abbr, ds in by_abbr.items():
        body_defs = (
            [d for d in ds if d.section != "abstract"] if ds[0].section == "abstract" else ds
        )
        for d in body_defs[1:]:
            issues.append(
                make_issue(
                    start=d.start,
                    end=d.end,
                    category=CATEGORY,
                    rule="abbr.redefined",
                    severity="info",
                    message=explain("issue.abbr_redefined", abbr=abbr),
                    suggestion=abbr,
                    lesson_slug=LESSON,
                )
            )
        first = ds[0]
        if not any(a > first.end for a, _ in uses.get(abbr, [])):
            issues.append(
                make_issue(
                    start=first.abbr_start,
                    end=first.abbr_end,
                    category=CATEGORY,
                    rule="abbr.unused",
                    severity="info",
                    message=explain("issue.abbr_unused", abbr=abbr),
                    lesson_slug=LESSON,
                )
            )
    return issues
