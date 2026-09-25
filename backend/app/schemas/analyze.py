from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import Issue, ProtectedSpan, Section


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_grade: float | None = Field(None, ge=4, le=20)


class MetricDetail(BaseModel):
    value: float
    score: float


class Stats(BaseModel):
    words: int
    sentences: int
    sentence_lengths: list[int]
    fk_grade: float


class Subscores(BaseModel):
    clarity: float | None
    rhythm: float | None
    vocabulary: float | None
    voice: float | None
    correctness: float | None


class AnalyzeResponse(BaseModel):
    score: float
    subscores: Subscores
    details: dict[str, dict[str, MetricDetail]]
    issues: list[Issue]
    stats: Stats
    sections: list[Section]
    protected: list[ProtectedSpan]
    languagetool: bool
