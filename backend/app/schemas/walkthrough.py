from __future__ import annotations

from pydantic import BaseModel


class KeyTerm(BaseModel):
    term: str
    start: int
    end: int
    definition: str | None = None
    source: str | None = None  # document | abbreviation | wordnet


class ParagraphOut(BaseModel):
    index: int  # paragraph index in the document segmentation
    start: int
    end: int
    section: str
    gist: str
    key_terms: list[KeyTerm]
    simplified: str
    grade_before: float
    grade_after: float


class ConceptNode(BaseModel):
    id: str
    label: str
    weight: float
    paragraphs: list[int]
    x: float
    y: float


class ConceptEdge(BaseModel):
    source: str
    target: str
    label: str | None = None
    weight: float


class ConceptMapOut(BaseModel):
    nodes: list[ConceptNode]
    edges: list[ConceptEdge]


class WalkthroughResponse(BaseModel):
    paragraphs: list[ParagraphOut]
    concept_map: ConceptMapOut
