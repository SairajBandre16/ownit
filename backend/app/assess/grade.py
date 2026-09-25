"""Grading (CLAUDE.md §9.4).

- cloze: exact, lemma or small-typo match (Levenshtein ≤ 2 on words longer than 5 letters);
  an abbreviation and its expansion are interchangeable.
- mcq / tf: exact option.
- open answers (viva, teach-back): coverage of the expected concepts (lemma, WordNet synonym or
  vector ≥ 0.7) and similarity to the source; score = 0.7 × coverage + 0.3 × similarity.
  Similarity is the cosine of the mean vectors of the content words (nouns, verbs, adjectives;
  whole-text vectors put any two English texts at ~0.9). It is rescaled to 0-1 from
  0.60 → 0.90, so an unrelated answer gets 0, not a free 30 points. Answers that mostly copy
  the source text are capped at 50: the point is to explain it in your own words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from app.assess.concepts import AnswerIndex, concept_match
from app.core.nlp import parse

SIM_FLOOR = 0.60
SIM_CEIL = 0.90
COPY_NGRAM = 4
COPY_SHARE = 0.6
COPY_CAP = 50
MIN_ANSWER_WORDS = 3
_ARTICLES = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _norm(s: str) -> str:
    s = re.sub(r"[^\w\s-]", " ", s.lower())
    s = _ARTICLES.sub("", " ".join(s.split()))
    return s.strip()


def _lemmas(s: str) -> list[str]:
    return [t.lemma_.lower() for t in parse(s) if not t.is_punct and not t.is_space]


def cloze_correct(answer: str, key: str, accepted: list[str] | None = None) -> bool:
    a = _norm(answer)
    if not a:
        return False
    for k in [key, *(accepted or [])]:
        n = _norm(k)
        if not n:
            continue
        if a == n or _lemmas(a) == _lemmas(n):
            return True
        aw, kw = a.split(), n.split()
        if len(aw) == len(kw) and all(
            x == y or (len(y) > 5 and levenshtein(x, y) <= 2) for x, y in zip(aw, kw, strict=True)
        ):
            return True
    return False


def choice_correct(answer: str, key: str) -> bool:
    return _norm(answer) == _norm(key)


# ---------------------------------------------------------------- open answers
@dataclass
class OpenGrade:
    score: float  # 0-100
    coverage: float  # 0-1
    similarity: float  # 0-1 (rescaled)
    covered: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)
    copied: bool = False
    feedback: str = ""


def content_vector(text: str) -> np.ndarray | None:
    """Unit mean vector of the content words of `text`."""
    toks = [
        t
        for t in parse(text)
        if t.has_vector and t.pos_ in ("NOUN", "PROPN", "VERB", "ADJ") and not t.is_stop
    ]
    if not toks:
        return None
    v = np.mean(np.array([t.vector for t in toks], dtype=np.float32), axis=0)
    n = float(np.linalg.norm(v))
    return v / n if n else None


def similarity(a: str, b: str) -> float:
    va, vb = content_vector(a), content_vector(b)
    if va is None or vb is None:
        return 0.0
    cos = float(np.dot(va, vb))
    return max(0.0, min(1.0, (cos - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR)))


def copied_share(answer: str, source: str) -> float:
    """Share of the answer's word 4-grams that appear verbatim in the source."""
    aw = re.findall(r"\w+", answer.lower())
    sw = re.findall(r"\w+", source.lower())
    if len(aw) < COPY_NGRAM:
        return 0.0
    grams = {tuple(sw[i : i + COPY_NGRAM]) for i in range(len(sw) - COPY_NGRAM + 1)}
    mine = [tuple(aw[i : i + COPY_NGRAM]) for i in range(len(aw) - COPY_NGRAM + 1)]
    return sum(g in grams for g in mine) / len(mine)


def _join(items: list[str]) -> str:
    items = [f"“{i}”" for i in items]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def grade_open(
    answer: str, concepts: list[str], source: str, aliases: dict[str, str] | None = None
) -> OpenGrade:
    words = len(answer.split())
    if words < MIN_ANSWER_WORDS:
        return OpenGrade(0, 0, 0, [], list(concepts), False, "Write at least one full sentence.")
    ans = AnswerIndex.build(answer)
    covered = [c for c in concepts if concept_match(c, ans, aliases)]
    missed = [c for c in concepts if c not in covered]
    coverage = len(covered) / len(concepts) if concepts else 0.0
    sim = similarity(answer, source)
    score = 100 * (0.7 * coverage + 0.3 * sim) if concepts else 100 * sim
    copied = words >= 8 and copied_share(answer, source) >= COPY_SHARE
    if copied:
        score = min(score, COPY_CAP)
    score = round(score, 1)

    if score >= 70:
        fb = "Good answer."
    elif score >= 40:
        fb = "Partly there."
    else:
        fb = "Not yet."
    if concepts:
        fb += f" You covered {len(covered)} of {len(concepts)} key ideas."
    if missed:
        fb += f" Missing: {_join(missed)}."
    if copied:
        fb += " Much of this is copied from the text; explain it in your own words."
    return OpenGrade(score, coverage, sim, covered, missed, copied, fb)
