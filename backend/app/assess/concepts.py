"""Concepts an answer should cover, and whether an answer covers them (CLAUDE.md §9.4).

Expected concepts are the document keyphrases found in the source span, topped up with its
main content words. A concept counts as covered when the answer contains it by lemma, by a
WordNet synonym, or by a word whose vector similarity is ≥ 0.7. Multi-word concepts need their
head word plus at least half of their words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from spacy.tokens import Doc, Token

from app.core.nlp import parse, zipf
from app.core.segment import Segmentation
from app.core.terms import GENERIC_MODIFIERS, _non_terms, noun_keyphrases

VECTOR_MATCH = 0.7
LIGHT_LEMMAS = {
    "be",
    "have",
    "do",
    "make",
    "use",
    "get",
    "take",
    "give",
    "show",
    "also",
    "however",
    "result",
    "value",
    "system",
    "way",
    "thing",
    "number",
    "part",
    "time",
    "conclusion",
    "introduction",
    "today",
    "world",
    "role",
    "order",
    "ability",
    "potential",
    "fact",
    "aspect",
    "area",
    "field",
    "kind",
    "type",
    "lot",
    "need",
    "case",
    "example",
    "addition",
    "term",
    "rest",
    "end",
    "purpose",
    "idea",
    "people",
    "year",
}
CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ"}
COMMON_ZIPF = 5.3  # "world", "people", "time": too common to be a concept worth checking
REFERENCE_WORDS = {"Fig", "Figs", "Figure", "Table", "Eq", "Equation", "Ref", "Sec", "Section"}


def body_text(seg: Segmentation) -> str:
    """The document without headings and a title line."""
    from app.walkthrough.service import is_title_line

    return "\n".join(
        p.text for p in seg.paragraphs if not p.is_heading and not is_title_line(p.text)
    )


def doc_keyphrases(seg: Segmentation, top: int = 30) -> list[str]:
    """Document keyphrases that occur in the body (not only in the title or headings), best
    first (memoised on the segmentation)."""
    key = f"assess.keyphrases.{top}"
    if key not in seg.cache:
        body = body_text(seg)
        out = []
        for p, _, _ in noun_keyphrases(seg, top=top):
            m = re.search(rf"(?<![\w-]){re.escape(p)}(?![\w-])", body, re.IGNORECASE)
            if m:
                out.append(m.group())  # as written in the body, not in the title
        seg.cache[key] = out
    return seg.cache[key]  # type: ignore[no-any-return]


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(phrase)}s?(?![\w-])", text, re.IGNORECASE) is not None


def span_concepts(
    seg: Segmentation, start: int, end: int, limit: int = 6, exclude: str = ""
) -> list[str]:
    """Concepts in [start, end): document keyphrases first, then its noun phrases and nouns.
    Concepts already named in `exclude` (e.g. the question) are left out, unless that leaves
    none."""
    text = seg.text[start:end]

    def collect(skip_named: bool) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()

        def add(c: str) -> None:
            low = c.lower()
            if low in seen or any(low in s or s in low for s in seen):
                return
            if skip_named and _contains(exclude, c):
                return
            seen.add(low)
            out.append(c)

        for p in doc_keyphrases(seg):
            if _contains(text, p):
                add(p)
        doc = parse(text)
        for chunk in doc.noun_chunks:
            toks = [t for t in chunk if _is_concept_word(t)]
            if toks and toks[0].lower_ in GENERIC_MODIFIERS:
                toks = toks[1:]  # "significant advancement" → "advancement"
            if len(toks) >= 2 and toks[-1].i == chunk.root.i:
                add(doc.text[toks[0].idx : toks[-1].idx + len(toks[-1])])
        for t in doc:
            if _is_concept_word(t) and t.pos_ in ("NOUN", "PROPN"):
                add(t.lower_ if t.pos_ == "NOUN" else t.text)
        return out

    out = collect(skip_named=bool(exclude))
    if not out and exclude:
        out = collect(skip_named=False)
    return out[:limit]


def _is_concept_word(t: Token) -> bool:
    return (
        t.pos_ in ("NOUN", "PROPN", "ADJ")
        and not t.is_stop
        and t.is_alpha
        and len(t.text) > 2
        and t.lemma_.lower() not in LIGHT_LEMMAS
        and t.lower_ not in _non_terms()  # units, section names
        and t.text not in REFERENCE_WORDS
        and zipf(t.lower_) <= COMMON_ZIPF
    )


# ---------------------------------------------------------------- matching
@lru_cache(maxsize=4096)
def _synonyms(lemma: str, pos: str) -> frozenset[str]:
    from nltk.corpus import wordnet as wn

    wn_pos = {"NOUN": wn.NOUN, "VERB": wn.VERB, "ADJ": wn.ADJ, "ADV": wn.ADV}.get(pos)
    if wn_pos is None:
        return frozenset()
    names: set[str] = set()
    for syn in wn.synsets(lemma, pos=wn_pos)[:3]:
        names |= {n.replace("_", " ").lower() for n in syn.lemma_names()}
    names.discard(lemma)
    return frozenset(names)


@dataclass
class AnswerIndex:
    """Lemmas, words and vectors of an answer, built once per answer."""

    lemmas: set[str]
    text: str
    vectors: np.ndarray  # (n, d) unit vectors of content words
    pos: list[str]

    @classmethod
    def build(cls, answer: str) -> AnswerIndex:
        doc = parse(answer)
        lemmas = {t.lemma_.lower() for t in doc} | {t.lower_ for t in doc}
        content = [t for t in doc if t.pos_ in CONTENT_POS and t.has_vector and not t.is_stop]
        vecs = np.array([t.vector / (t.vector_norm or 1.0) for t in content], dtype=np.float32)
        return cls(lemmas, answer.lower(), vecs, [t.pos_ for t in content])


def _token_match(tok: Token, ans: AnswerIndex) -> str | None:
    lemma = tok.lemma_.lower()
    if lemma in ans.lemmas or tok.lower_ in ans.lemmas:
        return "lemma"
    if any(s in ans.lemmas or (" " in s and s in ans.text) for s in _synonyms(lemma, tok.pos_)):
        return "synonym"
    if tok.has_vector and len(ans.vectors) and tok.pos_ in CONTENT_POS:
        v = tok.vector / (tok.vector_norm or 1.0)
        if float(np.max(ans.vectors @ v)) >= VECTOR_MATCH:
            return "vector"
    return None


def concept_match(
    concept: str, ans: AnswerIndex, aliases: dict[str, str] | None = None
) -> str | None:
    """How the answer covers `concept` ("phrase", "lemma", "synonym", "vector"), or None."""
    if _contains(ans.text, concept):
        return "phrase"
    for alias in (aliases or {}).get(concept.lower(), "").split("|"):
        if alias and _contains(ans.text, alias):
            return "phrase"
    doc: Doc = parse(concept)
    toks = [t for t in doc if not (t.is_punct or t.is_stop)] or list(doc)
    if not toks:
        return None
    head = next((t for t in toks if t.dep_ == "ROOT"), toks[-1])
    hows = {t.i: _token_match(t, ans) for t in toks}
    if hows[head.i] is None:
        return None
    matched = sum(1 for h in hows.values() if h)
    if matched * 2 < len(toks):
        return None
    kinds = [h for h in hows.values() if h]
    return "lemma" if all(k == "lemma" for k in kinds) else next(k for k in kinds if k != "lemma")


def aliases_for(seg: Segmentation) -> dict[str, str]:
    """concept -> "alias|alias" from "Full Name (ABBR)" pairs, both directions."""
    from app.walkthrough.glossary import abbreviation_pairs

    out: dict[str, str] = {}
    for abbr, full in abbreviation_pairs(seg).items():
        out[abbr.lower()] = full
        out[full.lower()] = abbr
    return out
