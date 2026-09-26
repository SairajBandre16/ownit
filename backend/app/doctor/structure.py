"""Report structure (CLAUDE.md §9.5): compare the headings with a lab/project report template
(Abstract, Introduction, Objectives, Theory, Methodology, Results, Discussion, Conclusion,
References), report core sections that are missing or out of order, and an abstract over 250
words. Documents with fewer than two recognised section headings are treated as essays and not
checked.
"""

from __future__ import annotations

from app.analyze.base import AnalyzerContext, make_issue
from app.core.explain import explain
from app.core.segment import Section
from app.schemas.common import Issue

CATEGORY = "engineering"
LESSON = "report-structure"
TEMPLATE = [
    "abstract",
    "introduction",
    "objectives",
    "theory",
    "methodology",
    "results",
    "discussion",
    "conclusion",
    "references",
]
CORE = {
    "introduction": "warn",
    "methodology": "warn",
    "results": "warn",
    "conclusion": "warn",
    "references": "info",
}
ABSTRACT_MAX_WORDS = 250
MIN_SECTIONS = 2
NICE = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "objectives": "Objectives",
    "theory": "Theory",
    "methodology": "Methodology",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "references": "References",
}


def _covers(sec: Section) -> set[str]:
    """Canonical sections a heading stands for ("Results and Discussion" covers both)."""
    out = {sec.name}
    h = sec.heading.lower()
    for name in TEMPLATE:
        if name.rstrip("s") in h or (name == "methodology" and "method" in h):
            out.add(name)
    return out & set(TEMPLATE)


def check(ctx: AnalyzerContext) -> list[Issue]:
    seg = ctx.seg
    named = [s for s in seg.sections if s.name in TEMPLATE and s.heading]
    if len({s.name for s in named}) < MIN_SECTIONS:
        return []
    issues: list[Issue] = []
    present: set[str] = set()
    for s in named:
        present |= _covers(s)

    # anchor document-level notes on the first line (usually the title)
    first = next((p for p in seg.paragraphs if p.text.strip()), None)
    a0, a1 = (first.start, first.end) if first else (0, 0)
    for name, severity in CORE.items():
        if name not in present:
            issues.append(
                make_issue(
                    start=a0,
                    end=a1,
                    category=CATEGORY,
                    rule="structure.missing",
                    severity=severity,  # type: ignore[arg-type]
                    message=explain("issue.section_missing", section=NICE[name]),
                    lesson_slug=LESSON,
                )
            )

    # order: each section should come after every earlier-template section already seen
    best = -1
    best_name = ""
    for s in named:
        pos = TEMPLATE.index(s.name)
        if pos < best:
            issues.append(
                make_issue(
                    start=s.start,
                    end=s.start + len(s.heading),
                    category=CATEGORY,
                    rule="structure.order",
                    severity="warn",
                    message=explain(
                        "issue.section_order", section=NICE[s.name], after=NICE[best_name]
                    ),
                    lesson_slug=LESSON,
                )
            )
        elif pos > best:
            best, best_name = pos, s.name

    for s in named:
        if s.name != "abstract":
            continue
        words = len(seg.text[s.start + len(s.heading) : s.end].split())
        if words > ABSTRACT_MAX_WORDS:
            issues.append(
                make_issue(
                    start=s.start,
                    end=s.start + len(s.heading),
                    category=CATEGORY,
                    rule="structure.abstract_long",
                    severity="warn",
                    message=explain("issue.abstract_long", n=words),
                    lesson_slug=LESSON,
                )
            )
    return issues
