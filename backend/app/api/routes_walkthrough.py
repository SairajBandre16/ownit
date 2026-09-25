from __future__ import annotations

from fastapi import APIRouter

from app.deps import cached, enforce_word_limit
from app.schemas.common import TextRequest
from app.schemas.walkthrough import WalkthroughResponse
from app.walkthrough.service import walkthrough

router = APIRouter(tags=["walkthrough"])


@router.post("/walkthrough", response_model=WalkthroughResponse)
def walkthrough_route(body: TextRequest) -> WalkthroughResponse:
    enforce_word_limit(body.text)
    return cached("walkthrough", {"text": body.text}, lambda: walkthrough(body.text))
