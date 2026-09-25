from __future__ import annotations

from fastapi import APIRouter

from app.core.nlp import get_languagetool, get_lm, get_nlp
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    nlp = get_nlp()
    lm = get_lm()
    return HealthResponse(
        status="ok",
        spacy=f"{nlp.meta['lang']}_{nlp.meta['name']}-{nlp.meta['version']}",
        lm=lm.name,
        lm_ready=lm.ready,
        languagetool=get_languagetool().available(),
    )
