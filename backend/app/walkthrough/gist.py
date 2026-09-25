"""One-line gist of a paragraph (extractive + compression, no generation).

1. Pick the paragraph's most central sentence (TextRank over sentence similarity).
2. Compress it: drop stock/wordy phrases, parentheticals, leading transitions and
   non-essential clauses (relative/adverbial clauses, appositives, long trailing PPs),
   keeping the main subject–verb–object skeleton.
"""

from __future__ import annotations

import re

import networkx as nx
import numpy as np
from spacy.tokens import Span

from app.core.graph import pagerank
from app.core.lexicon import PhraseLexicon, lexicon
from app.core.nlp import parse
from app.core.segment import Sentence
from app.humanize.text_utils import capitalize_first
from app.humanize.transforms.transition_vary import opening_transition

DROP_DEPS = {"advcl", "relcl", "appos", "parataxis", "npadvmod", "meta", "intj"}
MAX_WORDS = 22


def central_sentence(sentences: list[Sentence]) -> Sentence:
    """TextRank: the sentence most similar to the others."""
    if len(sentences) <= 2:
        return max(sentences, key=lambda s: s.words) if sentences else sentences[0]
    vecs = [np.asarray(s.span.vector, dtype=np.float32) for s in sentences]
    g = nx.Graph()
    for i in range(len(sentences)):
        g.add_node(i)
        for j in range(i + 1, len(sentences)):
            a, b = vecs[i], vecs[j]
            na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
            if na and nb:
                sim = float(np.dot(a, b) / (na * nb))
                if sim > 0:
                    g.add_edge(i, j, weight=sim)
    rank = pagerank(g) if g.number_of_edges() else {i: 1.0 for i in g}
    # small bias towards the first sentence (topic sentences come first in reports)
    rank[0] = rank.get(0, 0) * 1.15
    best = max(rank, key=lambda i: rank[i])
    return sentences[best]


def _drop_phrases(text: str) -> str:
    """Delete or condense stock/wordy phrases (the gist should be plain)."""
    for name in ("ai_style_phrases", "wordy_phrases", "fillers"):
        for m in reversed(lexicon(name).find(text, parse(text))):
            v = m.value
            repl = v.get("replacement") if isinstance(v, dict) else v
            if repl is None:
                continue
            new = PhraseLexicon.render(repl, m) if repl else ""
            text = text[: m.start] + new + text[m.end :]
    return re.sub(r"\s{2,}", " ", text)


COMPLEMENT_DEPS = {"dobj", "attr", "acomp", "oprd", "xcomp", "ccomp", "dative"}
REF_RE = re.compile(r"\b(?:Fig(?:ure)?s?|Tables?|Eqs?|Equations?)\.?\s*\(?\d+(?:\.\d+)?[a-z]?\)?")
FUNCTION_POS = {"ADP", "SCONJ", "CCONJ", "DET", "PART"}
MIN_GIST_WORDS = 6
OPEN_WORDS = {"how", "what", "why", "which", "that"}


def _atomic_groups(span: Span) -> list[list[int]]:
    """Token groups that must be kept or dropped together: hyphenated words ("game-changing")
    and figure/table/equation references ("Fig. 3")."""
    groups: list[list[int]] = []
    toks = list(span)
    i = 0
    while i < len(toks):
        j = i
        while (
            j + 1 < len(toks)
            and not toks[j].whitespace_
            and (toks[j + 1].text == "-" or toks[j].text == "-")
        ):
            j += 1
        if j > i:
            groups.append([t.i for t in toks[i : j + 1]])
        i = j + 1
    for m in REF_RE.finditer(span.text):
        s, e = span.start_char + m.start(), span.start_char + m.end()
        groups.append([t.i for t in span if s <= t.idx < e])
    return groups


def _skeleton(span: Span, drop_long_preps: bool) -> set[int]:
    root = span.root
    keep: set[int] = set()
    stack = [root]
    while stack:
        tok = stack.pop()
        keep.add(tok.i)
        verbal_conj = any(c.dep_ == "conj" and c.pos_ in ("VERB", "AUX") for c in tok.children)
        has_complement = any(c.dep_ in COMPLEMENT_DEPS for c in tok.children)
        for child in tok.children:
            if child.dep_ in DROP_DEPS:
                continue
            if (
                drop_long_preps
                and child.dep_ == "prep"
                and tok == root
                and has_complement
                and len(list(child.subtree)) > 6
            ):
                continue  # long trailing modifiers of the main verb
            if verbal_conj and (
                child.dep_ == "cc" or (child.dep_ == "conj" and child.pos_ in ("VERB", "AUX"))
            ):
                continue  # keep only the first coordinated clause
            stack.append(child)
    for group in _atomic_groups(span):
        if keep.intersection(group):
            keep.update(group)
    return keep


def _render(span: Span, keep: set[int]) -> str:
    # parentheticals ("(Fig. 2)", "(Smith, 2020)") are dropped whole, whatever their parse
    parens = [
        (span.start_char + m.start(), span.start_char + m.end())
        for m in re.finditer(r"\([^()]*\)", span.text)
    ]
    toks = [
        t
        for t in span
        if t.i in keep and not t.is_space and not any(s <= t.idx < e for s, e in parens)
    ]
    text = "".join(t.text_with_ws for t in toks).strip()
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip(" ,;:")


def _complete(span: Span, keep: set[int]) -> bool:
    """A skeleton that ends on a function word ("changed how", "consist of") is broken."""
    last = [t for t in span if t.i in keep and not t.is_punct and not t.is_space]
    if not last:
        return False
    end = last[-1]
    # a bare number at the end means a list was cut ("tested at 7" from "7, 14 and 28 days")
    return end.pos_ not in FUNCTION_POS and end.pos_ != "NUM" and end.lower_ not in OPEN_WORDS


def compress(span: Span) -> str:
    """Main-clause skeleton of a sentence; the full sentence if no clean skeleton exists."""
    for drop_long_preps in (True, False):
        keep = _skeleton(span, drop_long_preps)
        text = _render(span, keep)
        if _complete(span, keep) and len(text.split()) >= MIN_GIST_WORDS:
            return text
    return _render(span, {t.i for t in span})


def gist(sentences: list[Sentence]) -> str:
    if not sentences:
        return ""
    # heading-like fragments ("Results.") never carry the gist
    real = [s for s in sentences if s.words >= 4] or sentences
    sent = central_sentence(real)
    text = compress(sent.span)
    text = _drop_phrases(text)
    op = opening_transition(text)
    if op:
        text = text[op[2] :]
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;:")
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS]).rstrip(",;:") + "…"
    text = capitalize_first(text)
    text = re.sub(r"[\s,;:]+$", "", text)
    if text and text[-1] not in ".!?…":
        text += "."
    return text
