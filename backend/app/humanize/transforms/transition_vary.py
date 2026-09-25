"""transition_vary: vary or drop repeated sentence-initial transitions (CLAUDE.md §6.2.3).

Fires when the same transition was used within the previous 5 sentences, or when more than
one sentence in three starts with a transition.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.core.resources import load
from app.humanize.edits import local_rewrite
from app.humanize.types import Candidate, HumanizeContext, SentenceView, make_candidate

TRANSFORM = "transition_vary"
WINDOW = 5
# subordinators / fragments that can't replace "X, <clause>"
NOT_ADVERBIAL = {
    "because",
    "since",
    "as",
    "although",
    "though",
    "even though",
    "while",
    "whilst",
    "whereas",
    "such as",
    "including",
    "like",
    "e.g.",
    "consider",
    "when",
    "whenever",
    "once",
    "until",
    "after",
    "before",
    "as soon as",
    "just as",
    "as with",
    "given that",
    "seeing that",
    "now that",
    "inasmuch as",
    "insofar as",
    "this is because",
    "the reason is that",
    "the cause is that",
    "this means that",
    "this meant that",
    "it follows that",
    "the result is that",
    "the outcome is that",
    "that is why",
    "this is why",
    "which is why",
    "this led to",
    "this causes",
    "this results in",
    "so it is that",
    "therefore, it follows that",
    "a case in point is",
    "one example is",
    "another example is",
    "this can be seen in",
    "this is shown by",
    "take, for example",
    "not only that",
    "another point is that",
    "a further point is that",
    "another advantage is that",
    "also important",
    "especially important",
    "it is worth noting that",
    "it should be noted that",
    "it is important to note that",
    "note that",
    "remember that",
    "keep in mind that",
    "while it is true that",
    "it is true that",
    "to",
    "too",
    "plus",
    "ergo",
    "resultantly",
    "i mean",
    "actually",
    "really",
    "surely",
    "truly",
    "definitely",
    "anyway",
    "anyhow",
    "then",
    "again",
    "as well",
    "yet",
    "but",
    "so",
}


@lru_cache(maxsize=1)
def _groups() -> dict[str, list[str]]:
    return load("transitions")["groups"]  # type: ignore[no-any-return]


@lru_cache(maxsize=1)
def _lookup() -> dict[str, list[str]]:
    """transition (lowercase) -> groups it belongs to."""
    out: dict[str, list[str]] = {}
    for g, items in _groups().items():
        for t in items:
            out.setdefault(t.lower(), []).append(g)
    return out


@lru_cache(maxsize=1)
def _opener_re() -> re.Pattern[str]:
    alts = sorted(_lookup(), key=len, reverse=True)
    return re.compile(r"^\s*(" + "|".join(re.escape(a) for a in alts) + r")\s*,\s*", re.IGNORECASE)


def opening_transition(text: str) -> tuple[str, int, int] | None:
    """(transition lowercase, start, end-including-comma) if the sentence opens with one."""
    m = _opener_re().match(text)
    if not m:
        return None
    return m.group(1).lower(), m.start(1), m.end()


def alternatives(
    trans: str, tone: str, avoid: set[str], favourites: list[str] | None = None
) -> list[str]:
    tr = load("transitions")
    formal = {t.lower() for t in tr["formal"]}
    casual = {t.lower() for t in tr["casual"]}
    overused = {t.lower() for t in tr["ai_overused"]}
    pool: list[str] = []
    for g in _lookup().get(trans, []):
        for t in _groups()[g]:
            tl = t.lower()
            if tl == trans or tl in avoid or tl in NOT_ADVERBIAL or tl in pool:
                continue
            pool.append(tl)
    fav = [f.lower() for f in (favourites or [])]

    def rank(t: str) -> tuple[int, int, int, int]:
        tone_ok = (
            (t in formal)
            if tone == "academic"
            else (t in casual)
            if tone == "casual"
            else (t not in casual)
        )
        return (0 if t in fav else 1, 0 if t not in overused else 1, 0 if tone_ok else 1, len(t))

    return sorted(pool, key=rank)


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    found = opening_transition(view.text)
    if not found:
        return []
    trans, start, end = found
    if view.touches_protected(start, end):
        return []
    recent = ctx.chosen_openers[-WINDOW:]
    repeated = trans in recent
    window = ctx.chosen_openers[-2:] + [trans]
    dense = sum(1 for t in window if t) > 1  # > 1 transition in the last 3 sentences
    if not (repeated or dense):
        return []
    count = recent.count(trans) + 1
    favourites = (
        (ctx.profile or {}).get("_favourite_transitions") if isinstance(ctx.profile, dict) else None
    )
    out: list[Candidate] = []
    alts = alternatives(trans, ctx.tone, set(recent), favourites)
    text = view.text
    for alt in alts[:2]:
        word = alt[:1].upper() + alt[1:]
        ed = local_rewrite(
            text,
            start,
            end,
            f"{word}, ",
            TRANSFORM,
            "transform.transition_vary.replace",
            old=text[start:end].rstrip(", "),
            new=word,
            count=count,
        )
        if ed:
            c = make_candidate(view, [ed], (TRANSFORM,))
            if c:
                out.append(c)
    ed = local_rewrite(
        text,
        start,
        end,
        "",
        TRANSFORM,
        "transform.transition_vary.drop",
        old=text[start:end].rstrip(", "),
    )
    if ed:
        c = make_candidate(view, [ed], (TRANSFORM,))
        if c:
            out.append(c)
    return out
