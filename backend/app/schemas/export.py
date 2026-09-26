from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractResponse(BaseModel):
    text: str
    words: int
    warnings: list[str] = []


class OwnershipNote(BaseModel):
    score: float  # 0-100
    student_share: float  # 0-1
    passed_at: str | None = None  # ISO date the understanding checks were passed


class ExportDocxRequest(BaseModel):
    text: str = Field(..., min_length=1)
    title: str = "Untitled"
    author: str | None = None
    understanding: OwnershipNote | None = None  # adds a short ownership note at the end


class OwnershipPartIn(BaseModel):
    label: str
    weight: float
    value: float | None  # 0-1, None = does not apply
    detail: str


class GateRow(BaseModel):
    label: str
    value: float | None  # 0-100
    required: float
    passed: bool


class GlossaryRow(BaseModel):
    term: str
    definition: str | None = None
    source: str | None = None  # "yours" | "document" | "abbreviation" | "wordnet"


class VivaRow(BaseModel):
    question: str
    difficulty: str = ""
    answer: str = ""
    score: float = 0
    feedback: str = ""
    missed_concepts: list[str] = []


class QuizMiss(BaseModel):
    prompt: str
    answer_key: str
    your_answer: str = ""


class UnderstandingReportRequest(BaseModel):
    title: str = "Untitled"
    author: str | None = None
    date: str | None = None
    ownership_score: float = 0
    student_share: float = 0
    ownership_parts: list[OwnershipPartIn] = []
    gate: list[GateRow] = []
    gate_passed: bool = False
    mastered: list[str] = []
    weak: list[str] = []
    glossary: list[GlossaryRow] = []
    viva: list[VivaRow] = []
    quiz_total: float | None = None
    quiz_missed: list[QuizMiss] = []
    teachback_coverage: float | None = None
    teachback_explanation: str | None = None
    teachback_missed: list[str] = []
