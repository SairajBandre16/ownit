from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import Issue


class DoctorResponse(BaseModel):
    issues: list[Issue]  # category = "engineering"
    # issues per check: units, abbreviations, figures, tense, claims, structure
    counts: dict[str, int]
