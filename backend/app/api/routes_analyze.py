from __future__ import annotations

from fastapi import APIRouter

from app.analyze.score import run_analysis
from app.core.protect import protected_spans
from app.deps import cached, enforce_word_limit
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse, Stats, Subscores
from app.schemas.common import ProtectedSpan, Section

router = APIRouter(tags=["analyze"])


def analyze_text(text: str, target_grade: float | None = None) -> AnalyzeResponse:
    result = run_analysis(text, target_grade)
    seg = result.ctx.seg
    return AnalyzeResponse(
        score=result.score,
        subscores=Subscores(**result.subscores),
        details=result.details,  # type: ignore[arg-type]
        issues=result.issues,
        stats=Stats(
            words=result.words,
            sentences=len(result.sentence_lengths),
            sentence_lengths=result.sentence_lengths,
            fk_grade=result.metrics["clarity"].get("fk_grade", 0.0),
        ),
        sections=[
            Section(name=s.name, heading=s.heading, start=s.start, end=s.end) for s in seg.sections
        ],
        protected=[
            ProtectedSpan(start=p.start, end=p.end, kind=p.kind, text=p.text)
            for p in protected_spans(text)
        ],
        languagetool=result.subscores.get("correctness") is not None,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(body: AnalyzeRequest) -> AnalyzeResponse:
    enforce_word_limit(body.text)
    return cached(
        "analyze",
        {"text": body.text, "target_grade": body.target_grade},
        lambda: analyze_text(body.text, body.target_grade),
    )
