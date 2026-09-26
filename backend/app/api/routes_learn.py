from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.learn.lessons import all_lessons, get_lesson

router = APIRouter(tags=["learn"])


class LessonSummary(BaseModel):
    slug: str
    title: str
    summary: str
    group: str


class LessonOut(LessonSummary):
    markdown: str


@router.get("/lessons", response_model=list[LessonSummary])
def lessons() -> list[LessonSummary]:
    return [
        LessonSummary(slug=x.slug, title=x.title, summary=x.summary, group=x.group)
        for x in all_lessons().values()
    ]


@router.get("/lessons/{slug}", response_model=LessonOut)
def lesson(slug: str) -> LessonOut:
    x = get_lesson(slug)
    if x is None:
        raise HTTPException(status_code=404, detail="No such lesson.")
    return LessonOut(
        slug=x.slug, title=x.title, summary=x.summary, group=x.group, markdown=x.markdown
    )
