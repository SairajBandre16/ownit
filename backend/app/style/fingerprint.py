"""Voice Fingerprint (U1): a stylometric profile of the student's own writing (CLAUDE.md §9.1).

Features (rates per sentence or per 1,000 words where relevant):
  sentence length mean/SD, mean word length, MTLD, punctuation per sentence (comma, semicolon,
  colon, dash, parentheses, question mark), contractions, passive ratio, first-person pronouns,
  transition preferences, vocabulary tiers (wordfreq Zipf bins), sentence-opener POS mix,
  plus relative frequencies of 60 function words for Burrows' Delta.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from functools import lru_cache

from app.analyze.vocabulary import mtld
from app.core.nlp import zipf
from app.core.resources import load
from app.core.segment import segment
from app.humanize.transforms.transition_vary import opening_transition
from app.schemas.common import StyleProfile

CONTRACTION_RE = re.compile(
    r"\b\w+(?:n't|'re|'ve|'ll|'d|'m|'s)\b|\b(?:can't|won't)\b", re.IGNORECASE
)
FIRST_PERSON = {"i", "me", "my", "mine", "we", "us", "our", "ours", "myself", "ourselves"}
OPENER_POS = ["DET", "PRON", "NOUN", "PROPN", "ADP", "ADV", "SCONJ", "VERB", "ADJ", "NUM", "CCONJ"]
MIN_WORDS = 300


@lru_cache(maxsize=1)
def function_words() -> dict[str, dict[str, float]]:
    data = load("function_words")
    return {"mean": data["mean"], "sd": data["sd"], "words": data["words"]}  # type: ignore[dict-item]


def text_features(text: str) -> tuple[dict[str, float], dict[str, float], int]:
    """(features, function-word freqs per 1,000 words, word count) for a text."""
    seg = segment(text)
    sents = [s for s in seg.body_sentences if s.words > 0] or seg.sentences
    tokens = [t for s in sents for t in s.span]
    words = [t for t in tokens if t.is_alpha]
    n_words = max(len(words), 1)
    n_sents = max(len(sents), 1)
    lengths = [s.words for s in sents]
    raw = " ".join(s.text for s in sents)

    feats: dict[str, float] = {
        "sentence_length_mean": statistics.fmean(lengths) if lengths else 0.0,
        "sentence_length_sd": statistics.pstdev(lengths) if len(lengths) > 1 else 0.0,
        "word_length_mean": statistics.fmean(len(t.text) for t in words) if words else 0.0,
        "mtld": mtld([t.lower_ for t in words]),
        "commas_per_sentence": raw.count(",") / n_sents,
        "semicolons_per_sentence": raw.count(";") / n_sents,
        # colons/dashes between digits are ratios and ranges ("20:1", "10–20"), not style
        "colons_per_sentence": len(re.findall(r"(?<!\d):(?!\d)", raw)) / n_sents,
        "dashes_per_sentence": len(re.findall(r"(?<!\d)\s[-–—]\s(?!\d)|(?<!\d)—(?!\d)", raw))
        / n_sents,
        "parentheses_per_sentence": raw.count("(") / n_sents,
        "questions_per_sentence": raw.count("?") / n_sents,
        "contractions_per_sentence": len(CONTRACTION_RE.findall(raw)) / n_sents,
        "passive_ratio": sum(
            1 for s in sents if any(t.dep_ in ("nsubjpass", "auxpass") for t in s.span)
        )
        / n_sents,
        "first_person_per_1000": 1000 * sum(1 for t in words if t.lower_ in FIRST_PERSON) / n_words,
    }
    # vocabulary tiers
    tiers: Counter[str] = Counter()
    for t in words:
        z = zipf(t.lower_)
        tiers[
            "zipf_lt3" if z < 3 else "zipf_3_4" if z < 4 else "zipf_4_5" if z < 5 else "zipf_gt5"
        ] += 1
    for k in ("zipf_lt3", "zipf_3_4", "zipf_4_5", "zipf_gt5"):
        feats[k] = tiers[k] / n_words
    # sentence openers
    openers: Counter[str] = Counter()
    for s in sents:
        first = next((t for t in s.span if not (t.is_punct or t.is_space)), None)
        if first is not None:
            openers[first.pos_ if first.pos_ in OPENER_POS else "OTHER"] += 1
    for pos in OPENER_POS:
        feats[f"opener_{pos}"] = openers[pos] / n_sents
    # transition preferences (normalised over transitions used)
    trans: Counter[str] = Counter()
    for s in sents:
        op = opening_transition(s.text)
        if op:
            trans[op[0]] += 1
    total_trans = sum(trans.values())
    feats["transitions_per_sentence"] = total_trans / n_sents
    for name, n in trans.items():
        feats[f"trans:{name}"] = n / total_trans
    feats["_words"] = float(len(words))
    # function words per 1,000 words
    counts = Counter(t.lower_ for t in words)
    fw = {w: 1000 * counts[w] / n_words for w in function_words()["words"]}
    return feats, fw, len(words)


def fingerprint(samples: list[str]) -> StyleProfile:
    text = "\n\n".join(s.strip() for s in samples if s.strip())
    feats, fw, n = text_features(text)
    return StyleProfile(
        features={k: round(v, 4) for k, v in feats.items()},
        function_word_freqs={k: round(v, 3) for k, v in fw.items()},
        sample_word_count=n,
    )


def favourite_transitions(profile: StyleProfile | dict, top: int = 5) -> list[str]:
    feats = profile["features"] if isinstance(profile, dict) else profile.features
    items = [(k.removeprefix("trans:"), v) for k, v in feats.items() if k.startswith("trans:")]
    return [t for t, _ in sorted(items, key=lambda kv: -kv[1])[:top]]
