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
    vecs = [s.span.vector for s in sentences]
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


def compress(span: Span) -> str:
    """Main-clause skeleton of a sentence."""
    root = span.root
    keep = set()
    stack = [root]
    while stack:
        tok = stack.pop()
        keep.add(tok.i)
        for child in tok.children:
            if child.dep_ in DROP_DEPS:
                continue
            if child.dep_ == "prep" and tok == root and len(list(child.subtree)) > 6:
                continue  # long trailing modifiers of the main verb
            if child.dep_ == "cc" or (child.dep_ == "conj" and child.pos_ in ("VERB", "AUX")):
                continue  # keep only the first coordinated clause
            stack.append(child)
    toks = [t for t in span if t.i in keep and not t.is_space]
    text = "".join(t.text_with_ws for t in toks).strip()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;:")
    return text


def gist(sentences: list[Sentence]) -> str:
    if not sentences:
        return ""
    sent = central_sentence(sentences)
    text = compress(sent.span)
    if len(text.split()) < 4:
        text = sent.text
    text = _drop_phrases(text)
    op = opening_transition(text)
    if op:
        text = text[op[2] :]
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;:")
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS]).rstrip(",;:") + "…"
    text = capitalize_first(text)
    if text and text[-1] not in ".!?…":
        text += "."
    return text
