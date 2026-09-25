"""Turning a rewritten sentence (or a local rewrite) into minimal, well-formed edits."""

from __future__ import annotations

import re

from app.core.explain import explain
from app.humanize.text_utils import capitalize_first
from app.humanize.types import CATEGORY_BY_TRANSFORM, LocalEdit

_WORD = re.compile(r"\w")


def minimal_edit(old: str, new: str) -> tuple[int, int, str] | None:
    """Smallest [start, end) of `old` to replace with a substring of `new`, expanded to
    word boundaries so edits read as whole words."""
    if old == new:
        return None

    def w(c: str) -> bool:
        return bool(_WORD.match(c))

    p = 0
    while p < len(old) and p < len(new) and old[p] == new[p]:
        p += 1
    s = 0
    while s < len(old) - p and s < len(new) - p and old[-1 - s] == new[-1 - s]:
        s += 1
    # don't start or end an edit in the middle of a word
    while (
        p > 0 and w(old[p - 1]) and ((p < len(old) and w(old[p])) or (p < len(new) and w(new[p])))
    ):
        p -= 1
    while s > 0:
        q_old, q_new = len(old) - s, len(new) - s
        mid = w(old[q_old]) and (
            (q_old > 0 and w(old[q_old - 1])) or (q_new > 0 and w(new[q_new - 1]))
        )
        if not mid:
            break
        s -= 1
    return p, len(old) - s, new[p : len(new) - s]


def tidy(text: str, around: int, sentence_initial_cap: bool) -> str:
    """Clean punctuation/spacing near position `around` after a deletion or insertion."""
    lo = max(0, around - 4)
    hi = min(len(text), around + 4)
    window = text[lo:hi]
    window = re.sub(r"[ \t]{2,}", " ", window)
    window = re.sub(r"[ \t]+([,.;:!?])", r"\1", window)
    window = re.sub(r",\s*,", ",", window)
    window = re.sub(r"([.;:!?])\s*,", r"\1", window)
    out = text[:lo] + window + text[hi:]
    # nothing but punctuation/space before the first word -> strip it
    m = re.match(r"^[\s,;:]+", out)
    if m:
        out = out[m.end() :]
    if sentence_initial_cap:
        out = capitalize_first(out)
    return out


def edits_from_rewrite(
    old: str,
    new: str,
    transform: str,
    reason_key: str,
    **reason_values: object,
) -> list[LocalEdit]:
    """One LocalEdit (minimal window) for a whole-sentence rewrite."""
    win = minimal_edit(old, new)
    if win is None:
        return []
    start, end, replacement = win
    return [
        LocalEdit(
            start=start,
            end=end,
            replacement=replacement,
            transform=transform,
            reason=explain(reason_key, **reason_values),
            category=CATEGORY_BY_TRANSFORM[transform],
        )
    ]


def local_rewrite(
    text: str,
    start: int,
    end: int,
    replacement: str,
    transform: str,
    reason_key: str,
    category: str | None = None,
    **reason_values: object,
) -> LocalEdit | None:
    """Replace text[start:end] and tidy spacing/punctuation/capitalisation around it.
    Returns the minimal edit, or None if nothing changes."""
    starts_cap = text[:1].isupper()
    if not replacement:
        # parenthetical ", X," or trailing ", X." -> drop the surrounding commas too
        if text[max(0, start - 2) : start] == ", " and text[end : end + 1] == ",":
            start, end = start - 2, end + 1
        elif text[max(0, start - 2) : start] == ", " and text[end : end + 1] in (
            ".",
            ";",
            "!",
            "?",
        ):
            start -= 2
    new = text[:start] + replacement + text[end:]
    new = tidy(new, start + len(replacement) if replacement else start, starts_cap)
    win = minimal_edit(text, new)
    if win is None:
        return None
    s, e, rep = win
    return LocalEdit(
        start=s,
        end=e,
        replacement=rep,
        transform=transform,
        reason=explain(reason_key, **reason_values),
        category=category or CATEGORY_BY_TRANSFORM[transform],
    )
