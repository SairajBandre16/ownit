"""split_long: split sentences over 28 words (CLAUDE.md §6.2.4).

1. At a coordinating conjunction joining two independent clauses (both verbs have their own
   subject): "..., and the pump stopped" -> "... . The pump stopped".
2. At a non-restrictive relative clause that ends the sentence:
   "..., which reduces losses." -> "... . This reduces losses."
"""

from __future__ import annotations

from spacy.tokens import Span, Token

from app.humanize.edits import local_rewrite
from app.humanize.types import Candidate, HumanizeContext, LocalEdit, SentenceView, make_candidate

TRANSFORM = "split_long"
MIN_WORDS = 28
MIN_PART = 6
CONJ_OPENERS = {"and": "", "but": "However, ", "so": "As a result, ", "yet": "Yet "}
SUBJ = ("nsubj", "nsubjpass", "expl", "csubj")


def _words(tokens: list[Token]) -> int:
    return sum(1 for t in tokens if not (t.is_punct or t.is_space))


def _has_subject(tok: Token) -> bool:
    return any(c.dep_ in SUBJ for c in tok.children)


def _cc_splits(view: SentenceView) -> list[tuple[Token, Token]]:
    """(cc token, first token of the second clause) pairs that join independent clauses."""
    span: Span = view.span
    out = []
    for tok in span:
        if tok.dep_ != "cc" or tok.lower_ not in CONJ_OPENERS:
            continue
        head = tok.head
        if head.pos_ not in ("VERB", "AUX"):
            continue
        conj = next((c for c in head.children if c.dep_ == "conj" and c.i > tok.i), None)
        if conj is None or not (_has_subject(head) and _has_subject(conj)):
            continue
        if tok.i + 1 >= span.end:
            continue
        nxt = span.doc[tok.i + 1]
        left = [t for t in span if t.i < tok.i]
        right = [t for t in span if t.i > tok.i]
        if _words(left) < MIN_PART or _words(right) < MIN_PART:
            continue
        out.append((tok, nxt))
    return out


def _relative_split(view: SentenceView) -> tuple[Token, Token] | None:
    """(comma before 'which', 'which') when the relative clause runs to the sentence end."""
    span = view.span
    for tok in span:
        if tok.lower_ != "which" or tok.i == span.start:
            continue
        prev = span.doc[tok.i - 1]
        if prev.text != "," or tok.dep_ not in ("nsubj", "nsubjpass"):
            continue
        verb = tok.head
        if verb.dep_ != "relcl":
            continue
        # clause must reach the end of the sentence
        last = max(t.i for t in verb.subtree)
        tail = [t for t in span if t.i > last]
        if any(not t.is_punct for t in tail):
            continue
        left = [t for t in span if t.i < prev.i]
        right = [t for t in span if t.i > tok.i]
        if _words(left) < MIN_PART or _words(right) < 3:
            continue
        return prev, tok
    return None


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    if view.words <= MIN_WORDS:
        return []
    text = view.text
    out: list[Candidate] = []
    edits: list[LocalEdit] = []

    splits = _cc_splits(view)
    if splits:
        n_words = view.words

        # the split closest to the middle
        def balance(pair: tuple[Token, Token]) -> float:
            left = _words([t for t in view.span if t.i < pair[0].i])
            return abs(n_words / 2 - left)

        cc, nxt = min(splits, key=balance)
        cc_s, _ = view.local(cc)
        nxt_s, nxt_e = view.local(nxt)
        # start the edit at the end of the word before the conjunction (drops a comma)
        before = text[:cc_s].rstrip()
        cut = len(before.rstrip(","))
        opener = CONJ_OPENERS[cc.lower_]
        if ctx.tone == "casual" and cc.lower_ == "but":
            opener = "But "
        first = text[nxt_s:nxt_e]
        if view.token_protected(nxt) and first[:1].islower() and not opener:
            first_new = None
        else:
            first_new = first if opener else first[:1].upper() + first[1:]
            if opener and nxt.pos_ != "PROPN" and not first.isupper() and nxt.text != "I":
                first_new = first[:1].lower() + first[1:]
        if first_new is not None:
            ed = local_rewrite(
                text,
                cut,
                nxt_e,
                f". {opener}{first_new}",
                TRANSFORM,
                "transform.split_long.cc",
                n=n_words,
                conj=cc.text,
            )
            if ed:
                edits.append(ed)

    rel = _relative_split(view)
    if rel is not None:
        comma, which = rel
        c_s, _ = view.local(comma)
        _, w_e = view.local(which)
        antecedent = which.head.head
        pronoun = "These" if antecedent.tag_ in ("NNS", "NNPS") else "This"
        ed = local_rewrite(
            text, c_s, w_e, f". {pronoun}", TRANSFORM, "transform.split_long.relative", n=view.words
        )
        if ed:
            edits.append(ed)

    for ed in edits:
        c = make_candidate(view, [ed], (TRANSFORM,))
        if c:
            out.append(c)
    return out
