"""Question model shared by the generators and the grader."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

QuestionType = Literal["cloze", "mcq", "tf", "viva"]


@dataclass
class Question:
    id: str
    type: QuestionType
    prompt: str
    answer_key: str  # the term (cloze/mcq), "true"/"false" (tf), a model answer (viva)
    source_start: int  # the sentence the question comes from
    source_end: int
    concepts: list[str] = field(default_factory=list)  # what an answer should cover
    options: list[str] | None = None  # mcq
    accepted: list[str] = field(default_factory=list)  # other accepted cloze answers
    explanation: str = ""  # shown after answering (usually the source sentence)
    level: int | None = None  # viva ladder: 1 define, 2 how, 3 why, 4 compare/evaluate
    kind: str | None = None  # viva template or tf strategy
    target: str | None = None  # the concept a viva question is about
