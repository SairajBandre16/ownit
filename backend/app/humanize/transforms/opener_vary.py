"""opener_vary: break runs of sentences that open the same way (CLAUDE.md §6.2.8).

If at least 3 of the last 4 sentences (including this one) start with the same POS/lemma
("The …", "This …"), try clause_front, or move a trailing prepositional phrase of time/place
to the front: "The sample was heated in the furnace for two hours." ->
"For two hours, the sample was heated in the furnace."
"""

from __future__ import annotations

from spacy.tokens import Span

from app.humanize.edits import edits_from_rewrite
from app.humanize.text_utils import capitalize_first, lower_first
from app.humanize.transforms import clause_front
from app.humanize.types import Candidate, HumanizeContext, SentenceView, make_candidate
from app.style.objective import ADVERB_OPENERS, OPENER_CLASS, WORD_RE, opener_class

TRANSFORM = "opener_vary"
FRONTABLE_PREPS = {
    "in",
    "at",
    "on",
    "during",
    "after",
    "before",
    "for",
    "within",
    "over",
    "under",
    "throughout",
}


def cheap_key(text: str) -> str:
    """Opener signature without parsing: the first word for function words ("the", "this",
    "it", ...), otherwise a coarse class (NOUN / ADV / ...)."""
    m = WORD_RE.search(text)
    if not m:
        return ""
    w = m.group().lower()
    if w in OPENER_CLASS or w in ADVERB_OPENERS:
        return w
    return opener_class(text)


def repeated_opener(view: SentenceView, ctx: HumanizeContext) -> tuple[str, int] | None:
    keys = [cheap_key(t) for t in ctx.chosen[-3:]]
    mine = cheap_key(view.text)
    count = sum(1 for k in keys if k == mine) + 1
    return (mine, count) if count >= 3 else None


def front_pp(span: Span) -> str | None:
    root = span.root
    content = [t for t in span if not t.is_space]
    end_punct = content[-1] if content[-1].is_punct else None
    last = content[-2] if end_punct is not None else content[-1]
    preps = [
        c
        for c in root.children
        if c.dep_ == "prep" and c.i > root.i and c.lower_ in FRONTABLE_PREPS
    ]
    for prep in reversed(preps):
        pp = list(prep.subtree)
        ids = [t.i for t in pp]
        if ids != list(range(ids[0], ids[-1] + 1)) or ids[-1] != last.i or len(pp) < 2:
            continue
        doc = span.doc
        main = doc[content[0].i : ids[0]].text.rstrip(" ,")
        if len(main.split()) < 4:
            continue
        new = f"{capitalize_first(doc[ids[0] : ids[-1] + 1].text)}, {lower_first(main)}"
        return new + (end_punct.text if end_punct is not None else "")
    return None


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    rep = repeated_opener(view, ctx)
    if rep is None:
        return []
    key, count = rep
    word = next((t.text for t in view.span if not t.is_punct), key)
    out: list[Candidate] = []
    fronted = clause_front.front(view.span)
    if fronted:
        edits = edits_from_rewrite(
            view.text, fronted[0], TRANSFORM, "transform.opener_vary", count=count, opener=word
        )
        c = make_candidate(view, edits, (TRANSFORM,))
        if c:
            out.append(c)
    pp = front_pp(view.span)
    if pp:
        edits = edits_from_rewrite(
            view.text, pp, TRANSFORM, "transform.opener_vary", count=count, opener=word
        )
        c = make_candidate(view, edits, (TRANSFORM,))
        if c:
            out.append(c)
    return out
