"""Multiple-choice questions (CLAUDE.md §9.4).

The correct answer is the blanked term of a key sentence. Distractors are other keyphrases of
the same kind from the document (abbreviation ↔ abbreviation, named entity ↔ same entity
type, noun phrase ↔ noun phrase of similar length), most similar first, then WordNet sister
terms (co-hyponyms). A distractor never appears in the question's sentence.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache

import numpy as np

from app.assess.cloze import BLANK, display_form, occurrences, targets
from app.assess.keysent import KeySentence
from app.assess.types import Question
from app.core.nlp import parse, zipf
from app.core.segment import Segmentation

N_DISTRACTORS = 3
TOO_SIMILAR = 0.92
MIN_ZIPF = 2.5


def _is_abbr(term: str) -> bool:
    return (
        bool(re.fullmatch(r"[A-Z][A-Za-z0-9-]*[A-Z0-9][A-Za-z0-9-]*", term))
        and sum(c.isupper() for c in term) >= 2
    )


def term_kind(term: str, seg: Segmentation) -> str:
    if _is_abbr(term):
        return "abbr"
    for e in seg.doc.ents:
        if e.text.lower() == term.lower() and e.label_ in (
            "ORG",
            "PERSON",
            "GPE",
            "PRODUCT",
            "LAW",
        ):
            return e.label_
    return "np"


def _vec(text: str) -> np.ndarray:
    d = parse(text)
    return d.vector / (d.vector_norm or 1.0)


def _compatible(kind: str, term: str, cand: str, seg: Segmentation) -> bool:
    ck = term_kind(cand, seg)
    if kind == "abbr" or ck == "abbr":
        return kind == ck
    if kind != "np" or ck != "np":
        return kind == ck
    return abs(len(term.split()) - len(cand.split())) <= 1


@lru_cache(maxsize=2048)
def cohyponyms(term: str) -> tuple[str, ...]:
    """WordNet sister terms of `term` (or of its head word)."""
    from nltk.corpus import wordnet as wn

    words = term.lower().split()
    for key in ("_".join(words), words[-1]):
        synsets = wn.synsets(key, pos=wn.NOUN)[:2]
        if not synsets:
            continue
        out: list[str] = []
        for syn in synsets:
            for hyper in syn.hypernyms():
                for hypo in hyper.hyponyms():
                    if hypo == syn:
                        continue
                    name = hypo.lemma_names()[0].replace("_", " ")
                    if (
                        name.lower() != term.lower()
                        and min(zipf(w) for w in name.split()) >= MIN_ZIPF
                    ):
                        out.append(name)
        if out:
            return tuple(dict.fromkeys(out))
    return ()


def distractors(
    term: str, sentence: str, pool: list[str], seg: Segmentation, aliases: dict[str, str]
) -> list[str]:
    kind = term_kind(term, seg)
    low = term.lower()
    alias = aliases.get(low, "").lower()
    tv = _vec(term)
    cands: list[tuple[float, str]] = []
    seen: set[str] = set()
    for c in pool:
        cl = c.lower()
        if cl in seen or cl in (low, alias) or cl in low or low in cl:
            continue
        seen.add(cl)
        if occurrences(sentence, c) or not _compatible(kind, term, c, seg):
            continue
        sim = float(np.dot(tv, _vec(c)))
        if sim >= TOO_SIMILAR:
            continue
        cands.append((sim, display_form(c, seg.text)))
    cands.sort(key=lambda x: -x[0])
    out = [c for _, c in cands[:N_DISTRACTORS]]
    if len(out) < N_DISTRACTORS and kind == "np":
        extra = [
            c for c in cohyponyms(term) if not occurrences(sentence, c) and c.lower() not in seen
        ]
        extra.sort(key=lambda c: -float(np.dot(tv, _vec(c))))
        out += extra[: N_DISTRACTORS - len(out)]
    return out if len(out) == N_DISTRACTORS else []


def _shuffle(options: list[str], qid: str) -> list[str]:
    return sorted(options, key=lambda o: hashlib.sha1(f"{qid}:{o}".encode()).hexdigest())


def make_mcq(
    ks: KeySentence,
    keyphrases: list[str],
    seg: Segmentation,
    aliases: dict[str, str],
    qid: str,
    used_terms: set[str],
) -> Question | None:
    s = ks.sent
    for surface, a, b in targets(ks, keyphrases, seg):
        if surface.lower() in used_terms:
            continue
        alias = aliases.get(surface.lower(), "")
        m = re.match(r"\s*\(([^)]{1,12})\)", ks.text[b:])
        if m and m.group(1).lower() == alias.lower():
            b += m.end()
        elif alias and occurrences(ks.text, alias):
            continue
        key = display_form(surface, seg.text)
        wrong = distractors(key, ks.text, keyphrases, seg, aliases)
        if not wrong:
            continue
        return Question(
            id=qid,
            type="mcq",
            prompt=(ks.text[:a] + BLANK + ks.text[b:]).strip(),
            answer_key=key,
            options=_shuffle([key, *wrong], qid),
            source_start=s.start,
            source_end=s.end,
            concepts=[key],
            explanation=s.text.strip(),
        )
    return None
