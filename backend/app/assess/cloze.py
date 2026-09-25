"""Cloze questions (CLAUDE.md §9.4): blank the best keyphrase of a key sentence (or the term
of a definition sentence). Answers are graded with lemma and small-typo tolerance."""

from __future__ import annotations

import re

from app.assess.keysent import KeySentence
from app.assess.types import Question
from app.core.protect import detect_protected
from app.core.segment import Segmentation
from app.core.spans import SpanIndex

BLANK = "_____"
EXCLUDE_KINDS = {"citation", "quote", "equation", "code", "url", "number", "reference"}


def occurrences(text: str, phrase: str) -> list[tuple[int, int]]:
    return [
        (m.start(), m.end())
        for m in re.finditer(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", text, re.IGNORECASE)
    ]


def excluded_index(seg: Segmentation) -> SpanIndex:
    if "assess.excluded" not in seg.cache:
        seg.cache["assess.excluded"] = SpanIndex(
            (p.start, p.end) for p in detect_protected(seg.text) if p.kind in EXCLUDE_KINDS
        )
    return seg.cache["assess.excluded"]  # type: ignore[no-any-return]


def display_form(term: str, text: str) -> str:
    """ "Water scarcity" (capitalised only at a sentence start) -> "water scarcity"."""
    if len(term) > 1 and term[0].isupper() and not term[1].isupper():
        low = term[0].lower() + term[1:]
        if re.search(rf"(?<![\w-]){re.escape(low)}(?![\w-])", text):
            return low
    return term


def targets(
    ks: KeySentence, keyphrases: list[str], seg: Segmentation
) -> list[tuple[str, int, int]]:
    """Blankable terms of a sentence, best first: (surface, start, end) relative to the sentence.
    A term qualifies if it occurs once in the sentence, outside citations/numbers/quotes."""
    excluded = excluded_index(seg)
    out: list[tuple[str, int, int]] = []
    cands = [ks.definition.term] if ks.definition else []
    cands += keyphrases
    seen: set[str] = set()
    for c in cands:
        low = c.lower()
        if low in seen:
            continue
        seen.add(low)
        occ = occurrences(ks.text, c)
        if len(occ) != 1:
            continue
        a, b = occ[0]
        if excluded.overlaps(ks.start + a, ks.start + b):
            continue
        out.append((ks.text[a:b], a, b))
    return out


def make_cloze(
    ks: KeySentence,
    keyphrases: list[str],
    seg: Segmentation,
    aliases: dict[str, str],
    qid: str,
    used_terms: set[str],
) -> Question | None:
    s = ks.sent
    for surface, a, b in targets(ks, keyphrases, seg):
        if surface.lower() in used_terms:
            continue
        alias = aliases.get(surface.lower(), "")
        # "programmable logic controller (PLC)": blank the abbreviation too, it gives it away
        m = re.match(r"\s*\(([^)]{1,12})\)", ks.text[b:])
        if m and m.group(1).lower() == alias.lower():
            b += m.end()
        elif alias and occurrences(ks.text, alias):
            continue  # the other name is still visible in the sentence
        prompt = ks.text[:a] + BLANK + ks.text[b:]
        key = display_form(surface, seg.text)
        return Question(
            id=qid,
            type="cloze",
            prompt=prompt.strip(),
            answer_key=key,
            accepted=[alias] if alias else [],
            source_start=s.start,
            source_end=s.end,
            concepts=[key],
            explanation=s.text.strip(),
        )
    return None
