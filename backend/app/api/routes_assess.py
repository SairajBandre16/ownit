from __future__ import annotations

from fastapi import APIRouter

from app.assess.service import Result, generate, grade_all
from app.assess.teachback import teachback
from app.assess.types import Question
from app.assess.viva import SESSION_LENGTH, Turn, level_name, next_question
from app.core.segment import segment
from app.deps import cached, enforce_word_limit
from app.schemas.assess import (
    ConceptSource,
    GenerateRequest,
    GenerateResponse,
    GradeRequest,
    GradeResponse,
    QuestionOut,
    ResultOut,
    TeachbackRequest,
    TeachbackResponse,
    VivaNextRequest,
    VivaNextResponse,
)
from app.schemas.common import Span

router = APIRouter(tags=["assess"])


def to_out(q: Question) -> QuestionOut:
    return QuestionOut(
        id=q.id,
        type=q.type,
        prompt=q.prompt,
        options=q.options,
        answer_key=q.answer_key,
        accepted=q.accepted,
        source_span=Span(start=q.source_start, end=q.source_end),
        concepts=q.concepts,
        explanation=q.explanation,
        level=q.level,
        difficulty=level_name(q.level) if q.level else None,
        kind=q.kind,
    )


def from_out(q: QuestionOut) -> Question:
    return Question(
        id=q.id,
        type=q.type,
        prompt=q.prompt,
        answer_key=q.answer_key,
        source_start=q.source_span.start,
        source_end=q.source_span.end,
        concepts=q.concepts,
        options=q.options,
        accepted=q.accepted,
        explanation=q.explanation,
        level=q.level,
        kind=q.kind,
    )


def result_out(r: Result) -> ResultOut:
    return ResultOut(
        id=r.id,
        correct=r.correct,
        score=r.score,
        feedback=r.feedback,
        missed_concepts=r.missed_concepts,
        covered_concepts=r.covered_concepts,
        source_span=Span(start=r.source_start, end=r.source_end),
    )


@router.post("/assess/generate", response_model=GenerateResponse)
def assess_generate(body: GenerateRequest) -> GenerateResponse:
    enforce_word_limit(body.text)

    def run() -> GenerateResponse:
        qs = generate(segment(body.text), body.confusing_paragraphs, body.seed)
        return GenerateResponse(questions=[to_out(q) for q in qs])

    payload = {"text": body.text, "confusing": body.confusing_paragraphs, "seed": body.seed}
    return cached("assess.generate", payload, run)


@router.post("/assess/grade", response_model=GradeResponse)
def assess_grade(body: GradeRequest) -> GradeResponse:
    if body.text:
        enforce_word_limit(body.text)
    seg = segment(body.text) if body.text else None
    answers = {a.id: a.answer for a in body.answers}
    results, total = grade_all([from_out(q) for q in body.questions], answers, seg)
    return GradeResponse(results=[result_out(r) for r in results], total=total)


@router.post("/assess/viva/next", response_model=VivaNextResponse)
def assess_viva_next(body: VivaNextRequest) -> VivaNextResponse:
    enforce_word_limit(body.text)
    history = [Turn(t.question, t.answer, t.score, t.id, t.missed_concepts) for t in body.history]
    q = next_question(segment(body.text), history)
    if q is None:
        return VivaNextResponse(done=True, index=len(history), total=SESSION_LENGTH)
    return VivaNextResponse(
        done=False,
        index=len(history) + 1,
        total=SESSION_LENGTH,
        question=to_out(q),
        difficulty=level_name(q.level or 1),
        target_concepts=q.concepts,
    )


@router.post("/teachback", response_model=TeachbackResponse)
def teachback_route(body: TeachbackRequest) -> TeachbackResponse:
    enforce_word_limit(body.text)
    enforce_word_limit(body.explanation)
    r = teachback(segment(body.text), body.explanation)
    g = r.grade
    return TeachbackResponse(
        coverage=round(100 * g.coverage, 1),
        covered=g.covered,
        missed=g.missed,
        similarity=round(g.similarity, 3),
        score=g.score,
        feedback=g.feedback,
        copied=g.copied,
        missed_sources=[
            ConceptSource(concept=c, span=Span(start=s, end=e)) for c, (s, e) in r.sources.items()
        ],
    )
