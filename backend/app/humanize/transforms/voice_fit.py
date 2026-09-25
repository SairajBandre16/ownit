"""voice_fit (U1): nudge a sentence toward the student's own habits.

* Swap an opening transition for the student's own favourite from the same group
  ("Moreover," -> "Also," if the student writes "Also," a lot).
* Contraction rate and sentence-length targets are applied through `contractions` and the
  ranker's style_fit (length targets and function-word habits from the profile).
"""

from __future__ import annotations

from app.humanize.edits import local_rewrite
from app.humanize.transforms.transition_vary import NOT_ADVERBIAL, _lookup, opening_transition
from app.humanize.types import Candidate, HumanizeContext, SentenceView, make_candidate

TRANSFORM = "voice_fit"


def favourites(ctx: HumanizeContext) -> list[str]:
    if not isinstance(ctx.profile, dict):
        return []
    return [f for f in ctx.profile.get("_favourite_transitions", []) if f not in NOT_ADVERBIAL]


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    favs = favourites(ctx)
    if not favs:
        return []
    found = opening_transition(view.text)
    if not found:
        return []
    trans, start, end = found
    if trans in favs or view.touches_protected(start, end):
        return []
    groups = set(_lookup().get(trans, []))
    for fav in favs:
        if groups & set(_lookup().get(fav, [])) and fav not in ctx.chosen_openers[-2:]:
            word = fav[:1].upper() + fav[1:]
            ed = local_rewrite(
                view.text,
                start,
                end,
                f"{word}, ",
                TRANSFORM,
                "transform.voice_fit.transition",
                new=word,
            )
            if ed:
                c = make_candidate(view, [ed], (TRANSFORM,))
                return [c] if c else []
    return []
