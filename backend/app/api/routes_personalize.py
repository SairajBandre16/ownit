from __future__ import annotations

from fastapi import APIRouter

from app.deps import cached, enforce_word_limit
from app.personalize.generic_detector import find_spots
from app.schemas.common import TextRequest
from app.schemas.personalize import SpotOut, SpotsResponse

router = APIRouter(tags=["personalize"])


def spots_for(text: str) -> SpotsResponse:
    return SpotsResponse(spots=[SpotOut(**s.__dict__) for s in find_spots(text)])


@router.post("/personalize/spots", response_model=SpotsResponse)
def personalize_spots(body: TextRequest) -> SpotsResponse:
    enforce_word_limit(body.text)
    return cached("personalize", {"text": body.text}, lambda: spots_for(body.text))
