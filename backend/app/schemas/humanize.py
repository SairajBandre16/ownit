from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import Change, ProtectedSpan, StyleProfile, Tone


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    tone: Tone = "academic"
    intensity: int = Field(3, ge=1, le=5)
    keep_terms: list[str] = Field(default_factory=list, max_length=200)
    style_profile: StyleProfile | None = None


class HumanizeStats(BaseModel):
    sentences: int
    sentences_considered: int
    sentences_changed: int
    candidates: int
    rejected: dict[str, int]
    languagetool: bool
    seconds: float


class HumanizeResponse(BaseModel):
    text: str
    changes: list[Change]
    protected: list[ProtectedSpan]
    score_before: float
    score_after: float
    voice_match: float | None = None
    voice_match_before: float | None = None
    stats: HumanizeStats
