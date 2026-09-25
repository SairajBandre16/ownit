from __future__ import annotations

from pydantic import BaseModel


class SpotOut(BaseModel):
    id: str
    start: int  # generic phrase (or sentence) to highlight
    end: int
    insert_at: int  # where the student's answer is inserted (end of its sentence)
    pattern: str
    label: str
    prompt: str
    starter: str  # suggested opening words for the answer
    quote: str


class SpotsResponse(BaseModel):
    spots: list[SpotOut]
