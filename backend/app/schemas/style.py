from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import StyleProfile


class FingerprintRequest(BaseModel):
    samples: list[str] = Field(..., min_length=1, max_length=5)


class CompareRequest(BaseModel):
    text: str = Field(..., min_length=1)
    profile: StyleProfile


class StyleDifference(BaseModel):
    feature: str
    you: float
    text: float
    message: str


class CompareResponse(BaseModel):
    voice_match: float
    differences: list[StyleDifference]
