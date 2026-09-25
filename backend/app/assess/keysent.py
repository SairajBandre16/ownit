"""Key sentences for questions (CLAUDE.md §9.4): TextRank over sentence vectors, plus every
definition sentence ("X is a/an …", "X refers to …", "X is defined as …")."""

from __future__ import annotations

import re
from dataclasses import dataclass

import networkx as nx
import numpy as np
from spacy.tokens import Doc, Token

from app.core.graph import pagerank
from app.core.nlp import parse
from app.core.segment import Segmentation, Sentence

SKIP_SECTIONS = {"references", "acknowledgements", "appendix", "abstract"}
MIN_WORDS = 6
MAX_WORDS = 45
MAX_TERM_TOKENS = 6


@dataclass(frozen=True)
class Definition:
    term: str
    start: int  # absolute offsets of the term
    end: int
    body: str  # what the term is defined as


@dataclass
class KeySentence:
    sent: Sentence
    score: float  # TextRank centrality, 0-1
    definition: Definition | None
    confusing: bool = False
    offset: int = 0  # characters of stock opener stripped from the start of the sentence

    @property
    def text(self) -> str:
        """The sentence without stock openers ("Moreover, it is important to note that …"),
        which is what questions are made from."""
        rest = self.sent.text[self.offset :].rstrip()
        return rest[:1].upper() + rest[1:]

    @property
    def start(self) -> int:
        """Absolute offset of `text`."""
        return self.sent.start + self.offset

    @property
    def doc(self) -> Doc:
        """`text` parsed on its own (the whole-document parse can cross line breaks)."""
        return parse(self.text)


WRAPPER_RE = re.compile(
    r"(?:it\s+(?:is|was)\s+(?:evident|clear|obvious|apparent)\s+that"
    r"|it\s+(?:can|could)\s+be\s+(?:seen|observed|concluded|noted)\s+that"
    r"|it\s+(?:should|must)\s+be\s+(?:noted|mentioned|emphasi[sz]ed)\s+that)\s*,?\s*",
    re.IGNORECASE,
)


def opener_length(text: str) -> int:
    """Length of the stock opener at the start of a sentence: transitions ("Moreover,") and
    empty wrappers ("it is important to note that"), possibly several in a row."""
    from app.core.lexicon import lexicon
    from app.humanize.transforms.transition_vary import opening_transition

    pos = 0
    for _ in range(4):
        rest = text[pos:]
        op = opening_transition(rest)
        if op:
            pos += op[2]
        else:
            m = WRAPPER_RE.match(rest)
            hit = next(
                (
                    x
                    for name in ("ai_style_phrases", "wordy_phrases")
                    for x in lexicon(name).find(rest)
                    if x.start == 0
                    and (x.value.get("replacement") if isinstance(x.value, dict) else x.value) == ""
                ),
                None,
            )
            if m:
                pos += m.end()
            elif hit:
                pos += hit.end
            else:
                break
        while pos < len(text) and text[pos] in " ,":
            pos += 1
    return pos if len(text[pos:].split()) >= MIN_WORDS else 0


SENTENCE_END = re.compile(r"[.!?][\"'”’)\]]?\s*$")


def body_sentences(seg: Segmentation) -> list[Sentence]:
    from app.walkthrough.service import is_title_line

    headings = {p.index for p in seg.paragraphs if p.is_heading or is_title_line(p.text)}
    return [
        s
        for s in seg.sentences
        if s.paragraph not in headings
        and s.section not in SKIP_SECTIONS
        and MIN_WORDS <= s.words <= MAX_WORDS
        and SENTENCE_END.search(s.text)  # cut-off fragments make broken questions
        and not s.text.rstrip().endswith("?")
    ]


def textrank(sents: list[Sentence]) -> list[float]:
    """Centrality of each sentence (normalised so the best is 1)."""
    if not sents:
        return []
    if len(sents) < 3:
        return [1.0] * len(sents)
    vecs = [np.asarray(s.span.vector, dtype=np.float32) for s in sents]
    norms = [float(np.linalg.norm(v)) for v in vecs]
    g = nx.Graph()
    g.add_nodes_from(range(len(sents)))
    for i in range(len(sents)):
        for j in range(i + 1, len(sents)):
            if norms[i] and norms[j]:
                sim = float(np.dot(vecs[i], vecs[j]) / (norms[i] * norms[j]))
                if sim > 0.3:
                    g.add_edge(i, j, weight=sim)
    rank = pagerank(g) if g.number_of_edges() else dict.fromkeys(range(len(sents)), 1.0)
    top = max(rank.values()) or 1.0
    return [rank[i] / top for i in range(len(sents))]


def np_range(tok: Token, max_tokens: int = MAX_TERM_TOKENS) -> tuple[int, int] | None:
    """Char range (in its doc) of the noun phrase headed by `tok`: no leading determiner, no
    relative clause, stops before a parenthesis ("programmable logic controller (PLC)")."""
    if tok.pos_ == "PRON":
        return None
    drop: set[int] = set()
    for c in tok.children:
        if c.dep_ in ("relcl", "acl", "appos"):
            drop |= {t.i for t in c.subtree}
    toks = [t for t in tok.subtree if t.i not in drop]
    while toks and (toks[0].pos_ == "DET" or toks[0].is_punct):
        toks = toks[1:]
    for k, t in enumerate(toks):
        if t.text == "(":
            toks = toks[:k]
            break
    while toks and toks[-1].is_punct:
        toks.pop()
    if not toks or len(toks) > max_tokens:
        return None
    return toks[0].idx, toks[-1].idx + len(toks[-1])


DEFINITION_HINT = re.compile(r"\b(?:is|are)\s+(?:a|an)\b|\brefers?\s+to\b|\bdefined\s+as\b", re.I)


def find_definition(sent: Sentence) -> Definition | None:
    if not DEFINITION_HINT.search(sent.text):
        return None
    doc = parse(sent.text)
    root = next((t for t in doc if t.dep_ == "ROOT"), None)
    if root is None:
        return None
    subj = next((c for c in root.children if c.dep_ in ("nsubj", "nsubjpass")), None)
    if subj is None:
        return None
    body_start = None
    if root.lemma_ == "be":
        attr = next((c for c in root.children if c.dep_ == "attr"), None)
        if attr is not None and any(
            d.lower_ in ("a", "an") for d in attr.children if d.dep_ == "det"
        ):
            body_start = attr.left_edge.idx
    elif root.lemma_ == "refer" and any(
        c.dep_ == "prep" and c.lower_ == "to" for c in root.children
    ):
        to = next(c for c in root.children if c.dep_ == "prep" and c.lower_ == "to")
        body_start = to.idx + len(to.text) + 1
    elif root.lemma_ == "define" and subj.dep_ == "nsubjpass":
        as_ = next((c for c in root.children if c.dep_ == "prep" and c.lower_ == "as"), None)
        if as_ is not None:
            body_start = as_.idx + len(as_.text) + 1
    if body_start is None:
        return None
    rng = np_range(subj)
    if rng is None:
        return None
    term = doc.text[rng[0] : rng[1]]
    body = doc.text[body_start:].strip().rstrip(".")
    if len(body.split()) < 3 or not any(c.isalpha() for c in term):
        return None
    return Definition(term, sent.start + rng[0], sent.start + rng[1], body)


def _norm(s: str) -> str:
    return " ".join(s.split())


def key_sentences(seg: Segmentation, confusing: list[str] | None = None) -> list[KeySentence]:
    """Every usable body sentence with its centrality, definition and confusing flag."""
    sents = body_sentences(seg)
    ranks = textrank(sents)
    marked = [_norm(c) for c in confusing or [] if c.strip()]
    out = []
    for s, r in zip(sents, ranks, strict=True):
        t = _norm(s.text)
        out.append(
            KeySentence(
                sent=s,
                score=r,
                definition=find_definition(s),
                confusing=any(t in c for c in marked),
                offset=opener_length(s.text),
            )
        )
    return out
