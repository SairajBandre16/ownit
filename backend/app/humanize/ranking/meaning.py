"""Meaning similarity between an original sentence and a candidate.

meaning_sim = mean(spaCy vector cosine, content-lemma F1), where two lemmas match if they are
equal or share a WordNet synset (so a synonym swap doesn't count as lost meaning).

Candidates differ from their original only inside a few edits, so a candidate is not re-parsed:
its unchanged tokens reuse the original's lemmas/POS and only new words are lemmatised
(lemminflect); see `CandidateTokens`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from lemminflect import getAllLemmas
from spacy.lang.en.stop_words import STOP_WORDS
from spacy.tokens import Doc

from app.core.nlp import get_nlp

CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV", "NUM"}
LIGHT = {"be", "have", "do"}


@lru_cache(maxsize=16384)
def _synonyms(lemma: str) -> frozenset[str]:
    from nltk.corpus import wordnet as wn

    out = {lemma}
    for syn in wn.synsets(lemma)[:6]:
        for ln in syn.lemmas():
            out.add(ln.name().lower())
    return frozenset(out)


def parse_many(texts: Iterable[str]) -> list[Doc]:
    """Fast parse (tagger + lemmatizer + vectors; no parser/NER)."""
    nlp = get_nlp()
    return list(nlp.pipe(texts, disable=["parser", "ner"]))


def content_lemmas(doc: Doc) -> Counter[str]:
    return Counter(
        t.lemma_.lower()
        for t in doc
        if t.pos_ in CONTENT_POS and not t.is_stop and t.lemma_.lower() not in LIGHT and t.is_alpha
    )


def lemma_f1(a: Counter[str], b: Counter[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    matched = 0
    pool = Counter(b)
    for lemma, n in a.items():
        for _ in range(n):
            hit: str | None = lemma if pool[lemma] > 0 else None
            if hit is None:
                for x in pool:
                    if pool[x] > 0 and (x in _synonyms(lemma) or lemma in _synonyms(x)):
                        hit = x
                        break
            if hit is not None:
                pool[hit] -= 1
                matched += 1
    precision = matched / max(sum(b.values()), 1)
    recall = matched / max(sum(a.values()), 1)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _cos(va: Any, vb: Any) -> float:
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def cosine(a: Doc, b: Doc) -> float:
    if a.text == b.text:
        return 1.0
    return _cos(a.vector, b.vector)


def meaning_sim(orig: Doc, cand: Doc, ignore: frozenset[str] = frozenset()) -> float:
    """`ignore`: lemmas of words removed as empty phrases ("it is important to note that"),
    which carry no content and shouldn't count as lost meaning."""
    a = content_lemmas(orig)
    for lemma in ignore:
        a.pop(lemma, None)
    return (cosine(orig, cand) + lemma_f1(a, content_lemmas(cand))) / 2


# ---------------------------------------------------------------- fast candidate path


@dataclass
class CandidateTokens:
    """Lemmas + vector of a candidate derived from the original parse and its edits."""

    lemmas: Counter[str]
    vector: Any


def _guess_lemma(word: str) -> str:
    w = word.lower()
    for upos in ("VERB", "NOUN", "ADJ"):
        lem = getAllLemmas(w, upos=upos).get(upos)
        if lem:
            return lem[0]
    return w


def candidate_tokens(
    orig: Doc, cand_text: str, edits: list[tuple[int, int, int]]
) -> CandidateTokens:
    """`edits`: (orig_start, orig_end, new_len) in original-sentence offsets, sorted."""
    nlp = get_nlp()
    cdoc = nlp.make_doc(cand_text)
    # map candidate char offsets back to original offsets outside edits
    lemmas: Counter[str] = Counter()
    orig_by_start = {t.idx: t for t in orig}
    for tok in cdoc:
        o = _to_orig(tok.idx, edits)
        ot = orig_by_start.get(o) if o is not None else None
        if ot is not None and ot.text == tok.text:
            if (
                ot.pos_ in CONTENT_POS
                and not ot.is_stop
                and ot.lemma_.lower() not in LIGHT
                and ot.is_alpha
            ):
                lemmas[ot.lemma_.lower()] += 1
            continue
        if tok.is_alpha and tok.lower_ not in STOP_WORDS:
            lem = _guess_lemma(tok.text)
            if lem not in LIGHT:
                lemmas[lem] += 1
    vecs = [t.vector for t in cdoc if t.has_vector]
    vector = (
        np.mean(np.asarray(vecs), axis=0) if vecs else np.zeros(orig.vector.shape, dtype=np.float32)
    )
    return CandidateTokens(lemmas, vector)


def _to_orig(pos: int, edits: list[tuple[int, int, int]]) -> int | None:
    delta = 0
    for s, e, new_len in edits:
        ns = s + delta
        if pos < ns:
            break
        if pos < ns + new_len:
            return None  # inside new text
        delta += new_len - (e - s)
    return pos - delta


def meaning_sim_fast(
    orig: Doc, cand: CandidateTokens, ignore: frozenset[str] = frozenset()
) -> float:
    a = content_lemmas(orig)
    for lemma in ignore:
        a.pop(lemma, None)
    ov = (
        np.mean(np.asarray([t.vector for t in orig if t.has_vector]), axis=0)
        if len(orig)
        else orig.vector
    )
    return (_cos(ov, cand.vector) + lemma_f1(a, cand.lemmas)) / 2
