"""clause_front: move a trailing adverbial clause to the front, or a fronted one to the end.

"The pump stopped because the fuse blew."  <->  "Because the fuse blew, the pump stopped."

Only for adverbial clauses (advcl) introduced by because / when / although / if / after /
before / while / since / once / unless / whenever, and only when the clause is one contiguous
block at the end (or start) of the sentence.
"""

from __future__ import annotations

from spacy.tokens import Span, Token

from app.humanize.edits import edits_from_rewrite
from app.humanize.text_utils import capitalize_first, lower_first
from app.humanize.types import Candidate, HumanizeContext, SentenceView, make_candidate

TRANSFORM = "clause_front"
MARKERS = {
    "because",
    "when",
    "although",
    "though",
    "if",
    "after",
    "before",
    "while",
    "since",
    "once",
    "unless",
    "whenever",
    "as soon as",
}
MIN_MAIN = 3
MIN_CLAUSE = 3


def _marker(verb: Token) -> Token | None:
    return next((c for c in verb.children if c.dep_ == "mark" and c.lower_ in MARKERS), None)


def _block(span: Span, clause: list[Token]) -> tuple[int, int] | None:
    ids = [t.i for t in clause]
    if ids != list(range(min(ids), max(ids) + 1)):
        return None
    return min(ids), max(ids)


def front(span: Span) -> tuple[str, str] | None:
    """(new text, marker) moving a trailing advcl to the front."""
    root = span.root
    content = [t for t in span if not t.is_space]
    end_punct = content[-1] if content[-1].is_punct else None
    for verb in root.children:
        if verb.dep_ != "advcl" or verb.i < root.i:
            continue
        mark = _marker(verb)
        if mark is None:
            continue
        clause = list(verb.subtree)
        block = _block(span, clause)
        if block is None:
            continue
        start, end = block
        last_content = content[-2] if end_punct is not None else content[-1]
        if end != last_content.i or clause[0] != mark:
            continue
        main = [t for t in content if t.i < start and not (t.is_punct and t.i == start - 1)]
        if len([t for t in main if not t.is_punct]) < MIN_MAIN or len(clause) < MIN_CLAUSE:
            continue
        doc = span.doc
        clause_text = doc[start : end + 1].text
        main_text = doc[main[0].i : main[-1].i + 1].text.rstrip(" ,")
        new = f"{capitalize_first(clause_text)}, {lower_first(main_text)}"
        return new + (end_punct.text if end_punct is not None else ""), mark.lower_
    return None


def back(span: Span) -> tuple[str, str] | None:
    """(new text, marker) moving a fronted advcl to the end."""
    root = span.root
    content = [t for t in span if not t.is_space]
    end_punct = content[-1] if content[-1].is_punct else None
    for verb in root.children:
        if verb.dep_ != "advcl" or verb.i > root.i:
            continue
        mark = _marker(verb)
        if mark is None:
            continue
        clause = list(verb.subtree)
        block = _block(span, clause)
        if block is None:
            continue
        start, end = block
        if start != content[0].i or clause[0] != mark:
            continue
        doc = span.doc
        after = doc[end + 1] if end + 1 < span.end else None
        if after is None or after.text != ",":
            continue
        main_end = content[-2].i if end_punct is not None else content[-1].i
        main_text = doc[after.i + 1 : main_end + 1].text
        if len(main_text.split()) < MIN_MAIN:
            continue
        clause_text = doc[start : end + 1].text
        new = f"{capitalize_first(main_text)} {lower_first(clause_text)}"
        return new + (end_punct.text if end_punct is not None else ""), mark.lower_
    return None


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    out: list[Candidate] = []
    for fn, key in ((front, "transform.clause_front"), (back, "transform.clause_back")):
        res = fn(view.span)
        if not res:
            continue
        new, marker = res
        edits = edits_from_rewrite(view.text, new, TRANSFORM, key, marker=marker)
        c = make_candidate(view, edits, (TRANSFORM,))
        if c:
            out.append(c)
    return out
