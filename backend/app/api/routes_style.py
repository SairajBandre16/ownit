from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.deps import enforce_word_limit
from app.schemas.common import StyleProfile
from app.schemas.style import CompareRequest, CompareResponse, FingerprintRequest, StyleDifference
from app.style.delta import compare
from app.style.fingerprint import MIN_WORDS, fingerprint

router = APIRouter(prefix="/style", tags=["style"])


@router.post("/fingerprint", response_model=StyleProfile)
def style_fingerprint(body: FingerprintRequest) -> StyleProfile:
    joined = "\n\n".join(body.samples)
    enforce_word_limit(joined)
    words = len(joined.split())
    if words < MIN_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"Paste at least {MIN_WORDS} words of your own writing (you have {words}).",
        )
    return fingerprint(body.samples)


@router.post("/compare", response_model=CompareResponse)
def style_compare(body: CompareRequest) -> CompareResponse:
    enforce_word_limit(body.text)
    match, diffs = compare(body.text, body.profile)
    return CompareResponse(
        voice_match=match,
        differences=[
            StyleDifference(
                feature=d.feature,
                you=round(d.profile_value, 3),
                text=round(d.text_value, 3),
                message=d.message,
            )
            for d in diffs[:3]
        ],
    )
