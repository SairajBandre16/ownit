"""Assemble the walkthrough for a text: per-paragraph gist, key terms, simplified version,
plus the document concept map."""

from __future__ import annotations

from app.core.segment import segment
from app.schemas.walkthrough import (
    ConceptEdge,
    ConceptMapOut,
    ConceptNode,
    KeyTerm,
    ParagraphOut,
    WalkthroughResponse,
)
from app.walkthrough import concept_map
from app.walkthrough.gist import gist
from app.walkthrough.glossary import document_definitions, paragraph_terms
from app.walkthrough.simplify import simplify_paragraphs


def walkthrough(text: str) -> WalkthroughResponse:
    seg = segment(text)
    body = [
        p for p in seg.paragraphs if not p.is_heading and seg.section_at(p.start) != "references"
    ]
    doc_defs = document_definitions(seg)
    simple = simplify_paragraphs(text, [(p.start, p.end) for p in body]) if body else []
    paragraphs: list[ParagraphOut] = []
    for i, p in enumerate(body):
        sents = seg.sentences_in(p.index)
        terms = paragraph_terms(seg, p.start, p.end, doc_defs)
        simplified, grade_before, grade_after = simple[i]
        paragraphs.append(
            ParagraphOut(
                index=p.index,
                start=p.start,
                end=p.end,
                section=seg.section_at(p.start),
                gist=gist(sents),
                key_terms=[
                    KeyTerm(
                        term=t.term,
                        start=t.start,
                        end=t.end,
                        definition=t.definition,
                        source=t.source,
                    )
                    for t in terms
                ],
                simplified=simplified,
                grade_before=round(grade_before, 1),
                grade_after=round(grade_after, 1),
            )
        )
    cmap = concept_map.build(seg, [p.index for p in body])
    return WalkthroughResponse(
        paragraphs=paragraphs,
        concept_map=ConceptMapOut(
            nodes=[ConceptNode(**n.__dict__) for n in cmap.nodes],
            edges=[ConceptEdge(**e.__dict__) for e in cmap.edges],
        ),
    )
