"""Quiz generation and grading entry points (CLAUDE.md §9.4)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.assess.cloze import make_cloze
from app.assess.concepts import aliases_for, doc_keyphrases
from app.assess.grade import choice_correct, cloze_correct, grade_open
from app.assess.keysent import KeySentence, key_sentences
from app.assess.mcq import make_mcq
from app.assess.true_false import explain_false, make_tf
from app.assess.types import Question
from app.assess.viva import build_bank
from app.core.segment import Segmentation

# a 10-question quiz: 4 cloze, 3 MCQ, 3 true/false, interleaved
PLAN = ["cloze", "mcq", "tf", "cloze", "mcq", "tf", "cloze", "tf", "mcq", "cloze"]
N_VIVA_PREVIEW = 6
CONFUSING_BOOST = 0.6
DEFINITION_BOOST = 0.3


def _priority(ks: KeySentence, rng: random.Random, jitter: float) -> float:
    return (
        ks.score
        + (DEFINITION_BOOST if ks.definition else 0.0)
        + (CONFUSING_BOOST if ks.confusing else 0.0)
        + rng.uniform(0, jitter)
    )


def generate(
    seg: Segmentation, confusing: list[str] | None = None, seed: int = 0, n: int = 10
) -> list[Question]:
    """Quiz questions (cloze/mcq/tf) from the most central sentences, with extra weight on
    paragraphs the student marked confusing, followed by a few viva questions. `seed` > 0
    shuffles the choice of sentences for a fresh quiz."""
    keys = key_sentences(seg, confusing)
    rng = random.Random(seed)
    jitter = 0.35 if seed else 0.0
    ordered = sorted(keys, key=lambda k: -_priority(k, rng, jitter))
    keyphrases = doc_keyphrases(seg)
    aliases = aliases_for(seg)
    used_sents: set[int] = set()
    used_terms: set[str] = set()
    quiz: list[Question] = []
    n_false = n_true = 0
    plan = (PLAN * (n // len(PLAN) + 1))[:n]
    for i, kind in enumerate(plan):
        for ks in ordered:
            if ks.sent.index in used_sents:
                continue
            qid = f"q{i + 1}-{kind}-{ks.sent.start}"
            q: Question | None
            if kind == "cloze":
                q = make_cloze(ks, keyphrases, seg, aliases, qid, used_terms)
            elif kind == "mcq":
                q = make_mcq(ks, keyphrases, seg, aliases, qid, used_terms)
            else:
                want_false = n_false <= n_true
                q = make_tf(ks, keyphrases, seg, qid, want_false, rotation=i + seed)
            if q is None:
                continue
            if q.type == "tf":
                if q.answer_key == "false":
                    n_false += 1
                else:
                    n_true += 1
            used_sents.add(ks.sent.index)
            used_terms.add(q.answer_key.lower())
            quiz.append(q)
            break
    bank = build_bank(seg)
    viva: list[Question] = []
    for level in (1, 2, 3, 4, 1, 3):
        pick = next((q for q in bank if q.level == level and q not in viva), None)
        if pick is not None:
            viva.append(pick)
        if len(viva) >= N_VIVA_PREVIEW:
            break
    return quiz + viva


# ---------------------------------------------------------------- grading
@dataclass
class Result:
    id: str
    correct: bool | None  # closed questions
    score: float  # 0-100
    feedback: str
    missed_concepts: list[str]
    covered_concepts: list[str]
    source_start: int
    source_end: int


def grade_one(q: Question, answer: str, seg: Segmentation | None = None) -> Result:
    base = dict(id=q.id, source_start=q.source_start, source_end=q.source_end)
    if q.type in ("cloze", "mcq", "tf"):
        if q.type == "cloze":
            ok = cloze_correct(answer, q.answer_key, q.accepted)
        else:
            ok = choice_correct(answer, q.answer_key)
        if q.type == "tf":
            fb = ("Correct. " if ok else "Not quite. ") + (
                explain_false(q) if q.answer_key == "false" else "True: this is what the text says."
            )
        else:
            fb = (
                "Correct."
                if ok
                else f"The answer is “{q.answer_key}”. The text says: “{q.explanation}”"
            )
        return Result(
            correct=ok,
            score=100.0 if ok else 0.0,
            feedback=fb,
            missed_concepts=[] if ok else list(q.concepts),
            covered_concepts=list(q.concepts) if ok else [],
            **base,  # type: ignore[arg-type]
        )
    aliases = aliases_for(seg) if seg is not None else None
    g = grade_open(answer, q.concepts, q.answer_key or q.explanation, aliases)
    return Result(
        correct=None,
        score=g.score,
        feedback=g.feedback,
        missed_concepts=g.missed,
        covered_concepts=g.covered,
        **base,  # type: ignore[arg-type]
    )


def grade_all(
    questions: list[Question], answers: dict[str, str], seg: Segmentation | None = None
) -> tuple[list[Result], float]:
    results = [grade_one(q, answers.get(q.id, ""), seg) for q in questions]
    closed = [r for r in results if r.correct is not None]
    if closed:
        total = 100 * sum(1 for r in closed if r.correct) / len(closed)
    else:
        total = sum(r.score for r in results) / len(results) if results else 0.0
    return results, round(total, 1)
