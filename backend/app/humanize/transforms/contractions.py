"""contractions: use contractions in casual tone ("do not" -> "don't"); expand them in academic
tone ("don't" -> "do not"). With a voice profile, follow the student's own contraction habit."""

from __future__ import annotations

import re

from app.humanize.edits import local_rewrite
from app.humanize.types import Candidate, HumanizeContext, LocalEdit, SentenceView, make_candidate

TRANSFORM = "contractions"
CONTRACT = {
    "do not": "don't",
    "does not": "doesn't",
    "did not": "didn't",
    "is not": "isn't",
    "are not": "aren't",
    "was not": "wasn't",
    "were not": "weren't",
    "cannot": "can't",
    "can not": "can't",
    "could not": "couldn't",
    "would not": "wouldn't",
    "should not": "shouldn't",
    "will not": "won't",
    "has not": "hasn't",
    "have not": "haven't",
    "had not": "hadn't",
    "it is": "it's",
    "that is": "that's",
    "there is": "there's",
    "we are": "we're",
    "they are": "they're",
    "you are": "you're",
    "i am": "I'm",
    "we have": "we've",
    "they have": "they've",
    "i have": "I've",
    "we will": "we'll",
    "it will": "it'll",
    "let us": "let's",
}
EXPAND = {v.lower(): k for k, v in CONTRACT.items() if k not in ("can not",)} | {
    "can't": "cannot",
    "won't": "will not",
}
# phrases that must stay expanded (emphasis or not a real contraction context)
_CONTRACT_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(CONTRACT, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_EXPAND_RE = re.compile(
    r"\b("
    + "|".join(re.escape(k).replace("'", "['’]") for k in sorted(EXPAND, key=len, reverse=True))
    + r")(?![\w])",
    re.IGNORECASE,
)


def _match_case(new: str, old: str) -> str:
    return new[:1].upper() + new[1:] if old[:1].isupper() else new


def wants_contractions(ctx: HumanizeContext) -> bool | None:
    """True = contract, False = expand, None = leave alone."""
    profile = ctx.profile if isinstance(ctx.profile, dict) else None
    rate = (profile or {}).get("features", {}).get("contractions_per_sentence") if profile else None
    if ctx.tone == "casual":
        return True
    if ctx.tone == "academic":
        return False
    if rate is not None:
        return rate >= 0.2
    return None


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    mode = wants_contractions(ctx)
    if mode is None:
        return []
    text = view.text
    edits: list[LocalEdit] = []
    if mode:
        for m in _CONTRACT_RE.finditer(text):
            old = m.group(1)
            new = _match_case(CONTRACT[old.lower()], old)
            # "that is," as in "that is, ..." is a clarification, not a contraction site
            if old.lower() == "that is" and text[m.end() : m.end() + 1] == ",":
                continue
            ed = local_rewrite(
                text,
                m.start(1),
                m.end(1),
                new,
                TRANSFORM,
                "transform.contractions",
                old=old,
                new=new,
            )
            if ed and not any(ed.overlaps(e) for e in edits):
                edits.append(ed)
    else:
        for m in _EXPAND_RE.finditer(text):
            old = m.group(1)
            new = _match_case(EXPAND[old.lower().replace("’", "'")], old)
            ed = local_rewrite(
                text,
                m.start(1),
                m.end(1),
                new,
                TRANSFORM,
                "transform.expand_contraction",
                old=old,
                new=new,
            )
            if ed and not any(ed.overlaps(e) for e in edits):
                edits.append(ed)
    if not edits:
        return []
    c = make_candidate(view, edits, (TRANSFORM,))
    return [c] if c else []
