"""dash_tidy: replace dashes used as sentence punctuation with the plainer mark that does the
same job. Heavy dash use is a habit of generated drafts, and a comma, colon, full stop or
brackets usually says more precisely how the two parts relate.

- a pair around an aside ("X, a short aside, Y"): commas for a short aside without commas,
  brackets otherwise
- a single dash between two full clauses: a full stop (or a semicolon when the second part
  can't start a sentence cleanly)
- a single dash before a phrase: a comma when the phrase continues the sentence ("especially
  when ...", "which ..."), a colon when it explains or lists ("one thing: power")

Handles the em dash, a spaced en dash and a spaced double hyphen. Dashes between digits
(ranges) and dashes inside protected spans are left alone. Students whose own writing uses
dashes (voice profile) keep them.
"""

from __future__ import annotations

import re

from app.core.explain import explain
from app.core.nlp import parse
from app.humanize.types import (
    CATEGORY_BY_TRANSFORM,
    Candidate,
    HumanizeContext,
    LocalEdit,
    SentenceView,
    make_candidate,
)

TRANSFORM = "dash_tidy"
DASH_RE = re.compile(r"\s*\u2014\s*|\s+\u2013\s+|\s+--\s+")
# dashes per sentence in the student's own writing above which dashes are their style
OWN_STYLE_RATE = 0.15
SHORT_ASIDE_WORDS = 10
SUBJECT_DEPS = {"nsubj", "nsubjpass", "expl", "csubj"}
# the sentence before the dash announces what follows ("one thing", "the following")
CUE_RE = re.compile(
    r"\b(?:one|two|three|four|five|several|these|this|the following|as follows)\b"
    r"(?:\s+[\w-]+){0,2}$",
    re.IGNORECASE,
)
# a phrase starting with one of these continues the sentence, so it takes a comma
CONTINUING_POS = {"ADV", "ADP", "SCONJ", "CCONJ"}
CONTINUING_TAGS = {"VBG", "VBN", "WDT", "WP", "WRB"}


def dashes(text: str) -> list[tuple[int, int]]:
    """[start, end) of each dash used as punctuation, with the spaces around it."""
    out = []
    for m in DASH_RE.finditer(text):
        before = text[m.start() - 1 : m.start()]
        after = text[m.end() : m.end() + 1]
        if before.isdigit() and after.isdigit():
            continue  # a range such as 10-20
        out.append((m.start(), m.end()))
    return out


def _is_sentence(text: str) -> bool:
    """True if `text`, parsed on its own, is a full sentence: its root is a verb with a subject
    and it doesn't open with a linking word ("and", "which", "because") that needs a host."""
    doc = parse(text.strip())
    if not len(doc) or _continues(doc[0]):
        return False
    root = next((t for t in doc if t.dep_ == "ROOT"), None)
    return (
        root is not None
        and root.pos_ in ("VERB", "AUX")
        and any(c.dep_ in SUBJECT_DEPS for c in root.children)
    )


def _continues(tok) -> bool:  # type: ignore[no-untyped-def]
    return tok.pos_ in CONTINUING_POS or tok.tag_ in CONTINUING_TAGS or tok.lower_ == "that"


def _edit(start: int, end: int, replacement: str, key: str, **values: object) -> LocalEdit:
    return LocalEdit(
        start=start,
        end=end,
        replacement=replacement,
        transform=TRANSFORM,
        reason=explain(key, **values),
        category=CATEGORY_BY_TRANSFORM[TRANSFORM],
    )


def _pair(view: SentenceView, a: tuple[int, int], b: tuple[int, int]) -> list[LocalEdit]:
    text = view.text
    aside = text[a[1] : b[0]]
    words = len(aside.split())
    if "," not in aside and words <= SHORT_ASIDE_WORDS:
        close = "," if text[b[1] : b[1] + 1].isalnum() else ""
        return [
            _edit(a[0], a[1], ", ", "transform.dash_tidy.pair_commas", aside=aside),
            _edit(
                b[0],
                b[1],
                close + (" " if close else ""),
                "transform.dash_tidy.pair_commas",
                aside=aside,
            ),
        ]
    tail_punct = text[b[1] : b[1] + 1] in (".", ",", ";", ":", "!", "?", "")
    return [
        _edit(a[0], a[1], " (", "transform.dash_tidy.pair_brackets", aside=aside),
        _edit(
            b[0],
            b[1],
            ")" if tail_punct else ") ",
            "transform.dash_tidy.pair_brackets",
            aside=aside,
        ),
    ]


def _single(view: SentenceView, d: tuple[int, int]) -> list[LocalEdit]:
    text = view.text
    head_end, tail_start = d
    tail_end = len(text.rstrip(" .!?\"”'’)"))
    if len(text[:head_end].split()) < 2 or tail_start >= tail_end:
        return []
    head, tail = text[:head_end], text[tail_start:tail_end]
    head_sentence = _is_sentence(head)
    if not head_sentence:
        # "Heat, dust and vibration: all of these ..." sums up what came before
        return [_edit(head_end, tail_start, ": ", "transform.dash_tidy.colon")]
    if _is_sentence(tail):
        first = text[tail_start]
        if first.islower() and not view.touches_protected(tail_start, tail_start + 1):
            return [
                _edit(head_end, tail_start + 1, ". " + first.upper(), "transform.dash_tidy.stop")
            ]
        if first.isupper():
            return [_edit(head_end, tail_start, ". ", "transform.dash_tidy.stop")]
        return [_edit(head_end, tail_start, "; ", "transform.dash_tidy.semicolon")]
    if not _continues(parse(tail.strip())[0]) and CUE_RE.search(head.rstrip()):
        # "needs one thing: a stable supply"
        return [_edit(head_end, tail_start, ": ", "transform.dash_tidy.colon")]
    return [_edit(head_end, tail_start, ", ", "transform.dash_tidy.comma")]


def _own_style(ctx: HumanizeContext) -> bool:
    profile = ctx.profile if isinstance(ctx.profile, dict) else None
    rate = (profile or {}).get("features", {}).get("dashes_per_sentence")
    return rate is not None and rate >= OWN_STYLE_RATE


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    if _own_style(ctx):
        return []
    found = [d for d in dashes(view.text) if not view.touches_protected(d[0], d[1])]
    if not found or len(found) > 3:
        return []
    edits: list[LocalEdit] = []
    if len(found) >= 2:
        edits += _pair(view, found[0], found[1])
        if len(found) == 3:
            edits += _single(view, found[2])
    else:
        edits += _single(view, found[0])
    if not edits:
        return []
    c = make_candidate(view, edits, (TRANSFORM,))
    return [c] if c else []
