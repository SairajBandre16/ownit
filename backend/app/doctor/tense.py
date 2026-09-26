"""Tense per section (CLAUDE.md §9.5): Methodology and Results are mainly in the past tense,
Introduction and Theory mainly in the present. Outlier sentences are flagged; if a whole section
uses the other tense, one note is given at its heading instead.

Exempt: sentences that point at the report itself ("Table 2 shows …", "as shown in Fig. 3"),
interpretation verbs in Results ("this indicates …"), and history with a date or citation in
Introduction/Theory ("In 1821, Seebeck discovered …").
"""

from __future__ import annotations

import re

from spacy.tokens import Span

from app.analyze.base import AnalyzerContext, make_issue
from app.core.explain import explain
from app.core.nlp import parse
from app.core.segment import Sentence
from app.schemas.common import Issue

CATEGORY = "engineering"
LESSON = "tense"
EXPECTED = {
    "methodology": "past",
    "results": "past",
    "introduction": "present",
    "theory": "present",
}
MIN_SENTENCES = 3
REPORTING = {
    "show",
    "indicate",
    "suggest",
    "present",
    "summarize",
    "summarise",
    "list",
    "compare",
    "give",
    "illustrate",
    "depict",
    "mean",
    "imply",
    "demonstrate",
    "represent",
    "confirm",
    "agree",
    "appear",
    "seem",
    "explain",
    "follow",
}
HISTORY = {
    "develop",
    "invent",
    "propose",
    "introduce",
    "report",
    "discover",
    "publish",
    "describe",
    "find",
    "use",
    "show",
}
REF_RE = re.compile(r"\b(?:Fig(?:ure)?s?\.?|Tables?|Eq\.?|Section)\s*\(?\d", re.IGNORECASE)
YEAR_OR_CITE = re.compile(r"\b(?:1[89]|20)\d{2}\b|\[\d+|\(\w[^)]*\d{4}\)|et al\.")


def sentence_tense(span: Span) -> str | None:
    """ "past" / "present" (incl. future and modals) for the main verb, or None."""
    root = next((t for t in span if t.dep_ == "ROOT"), None)
    if root is None or root.pos_ not in ("VERB", "AUX"):
        return None
    auxes = [c for c in root.children if c.dep_ in ("aux", "auxpass") and c.i < root.i]
    head = auxes[0] if auxes else root
    if head.tag_ == "MD":
        return (
            "past"
            if head.lower_ in ("could", "would", "might") and root.tag_ == "VBN"
            else "present"
        )
    tense = head.morph.get("Tense", [])
    if head.tag_ in ("VBD",) or (tense and tense[0] == "Past" and head.tag_ != "VBN"):
        return "past"
    if head.tag_ in ("VBZ", "VBP") or (tense and tense[0] == "Pres"):
        return "present"
    return None


def _exempt(s: Sentence, span: Span, section: str) -> bool:
    if REF_RE.search(s.text):
        return True
    root = next((t for t in span if t.dep_ == "ROOT"), None)
    lemma = root.lemma_.lower() if root is not None else ""
    if section in ("results", "methodology") and lemma in REPORTING:
        return True
    return section in ("introduction", "theory") and (
        bool(YEAR_OR_CITE.search(s.text)) or lemma in HISTORY
    )


def check(ctx: AnalyzerContext) -> list[Issue]:
    issues: list[Issue] = []
    by_section: dict[int, list[tuple[Sentence, str, bool]]] = {}
    sections = ctx.seg.sections
    for s in ctx.seg.body_sentences:
        expected = EXPECTED.get(s.section)
        if expected is None:
            continue
        span = parse(s.text)[:]  # parsed on its own: the document parse can cross lines
        tense = sentence_tense(span)
        if tense is None:
            continue
        idx = next(i for i, sec in enumerate(sections) if sec.start <= s.start < sec.end)
        by_section.setdefault(idx, []).append((s, tense, _exempt(s, span, s.section)))

    for idx, rows in by_section.items():
        sec = sections[idx]
        expected = EXPECTED[sec.name]
        counted = [(s, t) for s, t, ex in rows if not ex]
        if len(counted) < MIN_SENTENCES:
            continue
        other = "present" if expected == "past" else "past"
        n_other = sum(1 for _, t in counted if t == other)
        name = sec.heading or sec.name.capitalize()
        if n_other > len(counted) / 2:
            end = sec.start + len(sec.heading) if sec.heading else counted[0][0].end
            start = sec.start if sec.heading else counted[0][0].start
            issues.append(
                make_issue(
                    start=start,
                    end=end,
                    category=CATEGORY,
                    rule="tense.section",
                    severity="info",
                    message=explain(
                        "issue.tense_section",
                        section=name,
                        found=other,
                        name=sec.name.capitalize(),
                        expected=expected,
                    ),
                    lesson_slug=LESSON,
                )
            )
            continue
        for s, t in counted:
            if t == other:
                issues.append(
                    make_issue(
                        start=s.start,
                        end=s.end,
                        category=CATEGORY,
                        rule="tense.outlier",
                        severity="info",
                        message=explain(
                            "issue.tense_outlier", section=name, expected=expected, found=other
                        ),
                        lesson_slug=LESSON,
                    )
                )
    return issues
