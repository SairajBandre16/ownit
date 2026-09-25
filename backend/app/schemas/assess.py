from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Span


class QuestionOut(BaseModel):
    id: str
    type: Literal["cloze", "mcq", "tf", "viva"]
    prompt: str
    options: list[str] | None = None
    answer_key: str
    accepted: list[str] = []
    source_span: Span
    concepts: list[str]
    explanation: str = ""
    level: int | None = None
    difficulty: str | None = None
    kind: str | None = None


class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    confusing_paragraphs: list[str] = []  # paragraph texts the student marked "Confusing"
    seed: int = 0  # > 0 picks a different set of sentences


class GenerateResponse(BaseModel):
    questions: list[QuestionOut]


class AnswerIn(BaseModel):
    id: str
    answer: str = ""


class GradeRequest(BaseModel):
    questions: list[QuestionOut]
    answers: list[AnswerIn]
    text: str | None = None  # optional: lets "PLC" match "programmable logic controller"


class ResultOut(BaseModel):
    id: str
    correct: bool | None  # None for open answers (viva)
    score: float  # 0-100
    feedback: str
    missed_concepts: list[str]
    covered_concepts: list[str]
    source_span: Span


class GradeResponse(BaseModel):
    results: list[ResultOut]
    total: float  # % correct (closed questions) or mean score (open answers)


class VivaTurnIn(BaseModel):
    question: str
    answer: str = ""
    score: float = 0
    id: str | None = None
    missed_concepts: list[str] | None = None


class VivaNextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    history: list[VivaTurnIn] = []


class VivaNextResponse(BaseModel):
    done: bool
    index: int  # 1-based number of this question in the session
    total: int
    question: QuestionOut | None = None
    difficulty: str | None = None
    target_concepts: list[str] = []


class TeachbackRequest(BaseModel):
    text: str = Field(..., min_length=1)
    explanation: str


class ConceptSource(BaseModel):
    concept: str
    span: Span


class TeachbackResponse(BaseModel):
    coverage: float  # 0-100
    covered: list[str]
    missed: list[str]
    similarity: float  # 0-1
    score: float  # 0-100: 0.7 × coverage + 0.3 × similarity
    feedback: str
    copied: bool
    missed_sources: list[ConceptSource]
