"""True/False questions (CLAUDE.md §9.4).

A true statement is a key sentence as written. A false one perturbs it: flip a comparative or
direction word (increase ↔ decrease, higher ↔ lower …), swap two numbers, swap two key terms,
or negate the main verb. A false statement must not match any sentence of the document.
"""

from __future__ import annotations

import re
from functools import lru_cache

from lemminflect import getInflection

from app.assess.cloze import occurrences
from app.assess.keysent import KeySentence
from app.assess.types import Question
from app.core.nlp import parse
from app.core.resources import load
from app.core.segment import Segmentation

NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?!\.?\d)")  # "25", "3.3" but not the 32 in "ESP32"
NEGATION = re.compile(r"\b(?:not|never|no|cannot|n't)\b", re.IGNORECASE)
STRATEGIES = ("flip", "numbers", "terms", "negate")
EXPLAIN = {
    "flip": "a direction or comparison word was reversed",
    "numbers": "two numbers were swapped",
    "terms": "two terms were swapped",
    "negate": "the statement was negated",
}


@lru_cache(maxsize=1)
def _flips() -> dict[str, str]:
    return load("question_templates")["flips"]  # type: ignore[no-any-return]


def _case(word: str, like: str) -> str:
    return word[:1].upper() + word[1:] if like[:1].isupper() else word


def flip(text: str) -> str | None:
    flips = _flips()
    pattern = r"\b(" + "|".join(re.escape(w) for w in sorted(flips, key=len, reverse=True)) + r")\b"
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    word = m.group(1)
    repl = _case(flips[word.lower()], word)
    return text[: m.start()] + repl + text[m.end() :]


def swap_numbers(text: str) -> str | None:
    nums = list(NUM_RE.finditer(text))
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            a, b = nums[i], nums[j]
            if float(a.group()) != float(b.group()):
                return (
                    text[: a.start()]
                    + b.group()
                    + text[a.end() : b.start()]
                    + a.group()
                    + text[b.end() :]
                )
    return None


def swap_terms(text: str, keyphrases: list[str]) -> str | None:
    found: list[tuple[int, int]] = []
    for p in keyphrases:
        occ = occurrences(text, p)
        if len(occ) == 1 and not any(occ[0][0] < e and s < occ[0][1] for s, e in found):
            found.append(occ[0])
        if len(found) == 2:
            break
    if len(found) < 2:
        return None
    (a1, a2), (b1, b2) = sorted(found)
    x, y = text[a1:a2], text[b1:b2]
    if x.lower() == y.lower():
        return None
    x2 = x[0].lower() + x[1:] if a1 == 0 and not x[1:2].isupper() else x
    y2 = y[0].upper() + y[1:] if a1 == 0 else y
    return text[:a1] + y2 + text[a2:b1] + x2 + text[b2:]


def negate(text: str) -> str | None:
    if NEGATION.search(text):
        return None
    doc = parse(text)
    root = next((t for t in doc if t.dep_ == "ROOT"), None)
    if root is None or root.pos_ not in ("VERB", "AUX"):
        return None
    aux = next((c for c in root.children if c.dep_ in ("aux", "auxpass") and c.i < root.i), None)
    if aux is not None:
        if aux.lower_ == "can":
            return text[: aux.idx] + _case("cannot", aux.text) + text[aux.idx + len(aux.text) :]
        end = aux.idx + len(aux.text)
        return text[:end] + " not" + text[end:]
    if root.lemma_ == "be":
        end = root.idx + len(root.text)
        return text[:end] + " not" + text[end:]
    do = {"VBD": "did", "VBZ": "does", "VBP": "do"}.get(root.tag_)
    if do is None:
        return None
    base = getInflection(root.lemma_, tag="VB")
    verb = base[0] if base else root.lemma_
    return text[: root.idx] + f"{do} not {verb}" + text[root.idx + len(root.text) :]


def make_false(
    text: str, keyphrases: list[str], order: tuple[str, ...] = STRATEGIES
) -> tuple[str, str] | None:
    for strategy in order:
        out = {
            "flip": lambda: flip(text),
            "numbers": lambda: swap_numbers(text),
            "terms": lambda: swap_terms(text, keyphrases),
            "negate": lambda: negate(text),
        }[strategy]()
        if out and out != text:
            return out, strategy
    return None


def make_tf(
    ks: KeySentence,
    keyphrases: list[str],
    seg: Segmentation,
    qid: str,
    want_false: bool,
    rotation: int = 0,
) -> Question | None:
    s = ks.sent
    text = ks.text.strip()
    base = dict(
        id=qid,
        type="tf",
        source_start=s.start,
        source_end=s.end,
        explanation=s.text.strip(),
        concepts=[p for p in keyphrases if occurrences(text, p)][:3],
    )
    if not want_false:
        return Question(prompt=text, answer_key="true", kind="true", **base)  # type: ignore[arg-type]
    # swapping two terms often gives an odd sentence, so it is the last resort
    main = ("flip", "numbers", "negate")
    order = main[rotation % 3 :] + main[: rotation % 3] + ("terms",)
    res = make_false(text, keyphrases, order)
    if res is None:
        return None
    statement, strategy = res
    norm = " ".join(statement.lower().split())
    if any(norm == " ".join(x.text.lower().split()) for x in seg.sentences):
        return None  # the "false" statement is actually in the document
    return Question(prompt=statement, answer_key="false", kind=strategy, **base)  # type: ignore[arg-type]


def explain_false(q: Question) -> str:
    how = EXPLAIN.get(q.kind or "", "the statement was changed")
    return f"False: {how}. The text says: “{q.explanation}”"
