"""Teach-back (CLAUDE.md §9.4, U5): the student explains the whole document in their own words.

Expected concepts are the most central concepts of the document (the concept map's top nodes).
Coverage and similarity use the same open-answer grader as the viva; similarity is measured
against a summary of the document (its most central sentences).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.assess.concepts import aliases_for, body_text, doc_keyphrases
from app.assess.grade import OpenGrade, grade_open
from app.assess.keysent import key_sentences
from app.core.segment import Segmentation
from app.walkthrough import concept_map

N_CONCEPTS = 8
SUMMARY_SENTENCES = 6


@dataclass
class TeachbackResult:
    grade: OpenGrade
    concepts: list[str]
    sources: dict[str, tuple[int, int]] = field(default_factory=dict)  # concept -> first sentence


def central_concepts(seg: Segmentation, n: int = N_CONCEPTS) -> list[str]:
    body = [p.index for p in seg.paragraphs if not p.is_heading]
    nodes = sorted(concept_map.build(seg, body).nodes, key=lambda x: -x.weight)
    text = body_text(seg)
    out: list[str] = []
    for node in nodes:
        # as written in the body: the title's "Design and Testing of …" is not a concept
        m = re.search(rf"(?<![\w-]){re.escape(node.label)}(?![\w-])", text, re.IGNORECASE)
        if m and len(out) < n:
            out.append(m.group())
    for p in doc_keyphrases(seg):
        if len(out) >= n:
            break
        if p.lower() not in {o.lower() for o in out}:
            out.append(p)
    return out


def summary(seg: Segmentation) -> str:
    keys = sorted(key_sentences(seg), key=lambda k: -k.score)[:SUMMARY_SENTENCES]
    return " ".join(k.sent.text.strip() for k in sorted(keys, key=lambda k: k.sent.start))


def teachback(seg: Segmentation, explanation: str) -> TeachbackResult:
    concepts = central_concepts(seg)
    grade = grade_open(explanation, concepts, summary(seg) or seg.text, aliases_for(seg))
    sources: dict[str, tuple[int, int]] = {}
    for c in grade.missed:
        pat = re.compile(rf"(?<![\w-]){re.escape(c)}", re.IGNORECASE)
        s = next((s for s in seg.sentences if pat.search(s.text)), None)
        if s is not None:
            sources[c] = (s.start, s.end)
    return TeachbackResult(grade, concepts, sources)
