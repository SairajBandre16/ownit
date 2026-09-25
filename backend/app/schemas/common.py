"""Shared API models (CLAUDE.md §8). All offsets are [start, end) into the request text."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warn", "error"]
ChangeCategory = Literal["clarity", "rhythm", "vocabulary", "voice", "grammar"]
Tone = Literal["academic", "neutral", "casual"]


class Span(BaseModel):
    start: int
    end: int


class Issue(Span):
    id: str
    category: str
    rule: str
    severity: Severity
    message: str
    suggestion: str | None = None
    lesson_slug: str | None = None


class Change(BaseModel):
    id: str
    orig_start: int
    orig_end: int
    new_start: int
    new_end: int
    original: str
    replacement: str
    transform: str
    category: ChangeCategory
    reason: str
    confidence: float


class ProtectedSpan(Span):
    kind: str
    text: str


class StyleProfile(BaseModel):
    features: dict[str, float]
    function_word_freqs: dict[str, float]
    sample_word_count: int


class Section(Span):
    name: str
    heading: str


class HealthResponse(BaseModel):
    status: str
    spacy: str
    lm: Literal["kenlm", "fallback"]
    lm_ready: bool
    languagetool: bool


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)
