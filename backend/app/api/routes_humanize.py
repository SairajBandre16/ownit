from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.analyze.score import quick_score
from app.deps import cached, enforce_word_limit
from app.humanize.pipeline import humanize
from app.schemas.common import Change, ProtectedSpan
from app.schemas.humanize import HumanizeRequest, HumanizeResponse, HumanizeStats

router = APIRouter(tags=["humanize"])


def run_humanize(body: HumanizeRequest) -> HumanizeResponse:
    profile: dict[str, Any] | None = body.style_profile.model_dump() if body.style_profile else None
    out = humanize(
        body.text,
        tone=body.tone,
        intensity=body.intensity,
        keep_terms=tuple(body.keep_terms),
        profile=profile,
    )
    voice_before = voice_after = None
    if body.style_profile is not None:
        from app.style.delta import voice_match

        voice_before = voice_match(body.text, body.style_profile)
        voice_after = voice_match(out.text, body.style_profile)
    return HumanizeResponse(
        text=out.text,
        changes=[Change(**c.__dict__) for c in out.changes],
        protected=[
            ProtectedSpan(start=p.start, end=p.end, kind=p.kind, text=body.text[p.start : p.end])
            for p in out.protected
        ],
        score_before=quick_score(body.text),
        score_after=quick_score(out.text),
        voice_match=voice_after,
        voice_match_before=voice_before,
        stats=HumanizeStats(**out.stats),
    )


@router.post("/humanize", response_model=HumanizeResponse)
def humanize_route(body: HumanizeRequest) -> HumanizeResponse:
    enforce_word_limit(body.text)
    return cached("humanize", body.model_dump(), lambda: run_humanize(body))
