"""Voice Match: how close a text is to a student's Voice Fingerprint (CLAUDE.md §9.1).

voice_match = 100 × (1 − normalised distance), where the distance combines
  * Burrows' Delta on the 60 function words (weight 0.5): mean |z_text − z_profile| with z-scores
    from WikiText reference statistics, and
  * a z-scored Euclidean distance on the other stylometric features (weight 0.5), scaled by
    typical between-writer spreads.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.schemas.common import StyleProfile
from app.style.fingerprint import function_words, text_features

# typical spread of each feature between writers (used to z-score differences)
FEATURE_SCALE: dict[str, float] = {
    "sentence_length_mean": 5.0,
    "sentence_length_sd": 4.0,
    "word_length_mean": 0.35,
    "mtld": 25.0,
    "commas_per_sentence": 0.7,
    "semicolons_per_sentence": 0.15,
    "colons_per_sentence": 0.15,
    "dashes_per_sentence": 0.2,
    "parentheses_per_sentence": 0.25,
    "questions_per_sentence": 0.1,
    "contractions_per_sentence": 0.3,
    "passive_ratio": 0.2,
    "first_person_per_1000": 15.0,
    "transitions_per_sentence": 0.15,
    "zipf_lt3": 0.04,
    "zipf_3_4": 0.05,
    "zipf_4_5": 0.06,
    "zipf_gt5": 0.08,
    "opener_DET": 0.15,
    "opener_PRON": 0.12,
    "opener_ADP": 0.1,
    "opener_ADV": 0.1,
    "opener_SCONJ": 0.08,
    "opener_NOUN": 0.1,
}
# Distances are mapped linearly from "same writer" (lo) to "completely different" (hi).
DELTA_RANGE = (0.35, 1.6)  # Burrows' Delta
FEATURE_RANGE = (0.4, 2.2)  # RMS z-distance
PRIOR_WORDS = 250  # short texts are shrunk towards reference English (Bayesian smoothing)
LENGTH_SENSITIVE = {"mtld"}  # unreliable below ~200 words


@dataclass
class Difference:
    feature: str
    text_value: float
    profile_value: float
    z: float
    message: str


def burrows_delta(
    fw_text: dict[str, float], fw_profile: dict[str, float], n_words: int = 1000
) -> float:
    ref = function_words()
    total = 0.0
    words = ref["words"]
    weight = n_words / (n_words + PRIOR_WORDS)
    for w in words:  # type: ignore[union-attr]
        mean, sd = ref["mean"][w], ref["sd"][w]  # type: ignore[index]
        rate = weight * fw_text.get(w, 0.0) + (1 - weight) * mean
        zt = (rate - mean) / sd
        zp = (fw_profile.get(w, 0.0) - mean) / sd
        total += abs(zt - zp)
    return total / len(words)  # type: ignore[arg-type]


def feature_distance(
    feats: dict[str, float], profile: dict[str, float]
) -> tuple[float, list[tuple[str, float]]]:
    zs: list[tuple[str, float]] = []
    short = feats.get("_words", 1000) < 200
    for name, scale in FEATURE_SCALE.items():
        if short and name in LENGTH_SENSITIVE:
            continue
        if name in feats and name in profile:
            zs.append((name, (feats[name] - profile[name]) / scale))
    if not zs:
        return 0.0, []
    rms = math.sqrt(sum(z * z for _, z in zs) / len(zs))
    return rms, zs


def _message(name: str, text_v: float, prof_v: float) -> str:
    more = text_v > prof_v
    t, p = round(text_v, 1), round(prof_v, 1)
    templates = {
        "sentence_length_mean": (
            f"Your sentences are usually {'shorter' if more else 'longer'} "
            f"(avg {p:g} vs {t:g} words)."
        ),
        "sentence_length_sd": (
            f"You vary sentence length {'less' if more else 'more'} than this text "
            f"(spread {p:g} vs {t:g} words)."
        ),
        "word_length_mean": f"You use {'shorter' if more else 'longer'} words on average ({p:.2f} vs {t:.2f} letters).",
        "mtld": f"Your vocabulary is {'less' if more else 'more'} varied than this text.",
        "commas_per_sentence": f"You use {'fewer' if more else 'more'} commas ({p:g} vs {t:g} per sentence).",
        "semicolons_per_sentence": f"You {'rarely' if more else 'often'} use semicolons.",
        "colons_per_sentence": f"You {'rarely' if more else 'often'} use colons.",
        "dashes_per_sentence": f"You {'rarely' if more else 'often'} use dashes.",
        "parentheses_per_sentence": f"You use {'fewer' if more else 'more'} brackets.",
        "questions_per_sentence": f"You ask {'fewer' if more else 'more'} questions.",
        "contractions_per_sentence": f"You use {'fewer' if more else 'more'} contractions (like “don't”).",
        "passive_ratio": (
            f"You write in the passive voice {'less' if more else 'more'} often "
            f"({round(prof_v * 100)}% vs {round(text_v * 100)}% of sentences)."
        ),
        "first_person_per_1000": f"You say “I/we” {'less' if more else 'more'} often.",
        "transitions_per_sentence": (
            f"You start {'fewer' if more else 'more'} sentences with linking words like “Moreover”."
        ),
        "zipf_lt3": f"You use {'fewer' if more else 'more'} rare words.",
        "zipf_3_4": f"You use {'fewer' if more else 'more'} uncommon words.",
        "zipf_4_5": f"You use {'fewer' if more else 'more'} mid-frequency words.",
        "zipf_gt5": f"You use {'fewer' if more else 'more'} everyday words.",
        "opener_DET": f"You start {'fewer' if more else 'more'} sentences with “The/This/A”.",
        "opener_PRON": f"You start {'fewer' if more else 'more'} sentences with “I/We/It”.",
        "opener_ADP": f"You start {'fewer' if more else 'more'} sentences with a phrase like “In the lab…”.",
        "opener_ADV": f"You start {'fewer' if more else 'more'} sentences with an adverb.",
        "opener_SCONJ": f"You start {'fewer' if more else 'more'} sentences with “Because/When/If…”.",
        "opener_NOUN": f"You start {'fewer' if more else 'more'} sentences with a noun.",
    }
    return templates.get(name, f"{name}: {p:g} (you) vs {t:g} (this text)")


def compare(text: str, profile: StyleProfile) -> tuple[float, list[Difference]]:
    """(voice_match 0-100, differences sorted by importance)."""
    feats, fw, n = text_features(text)
    delta = burrows_delta(fw, profile.function_word_freqs, n)
    rms, zs = feature_distance(feats, profile.features)
    distance = 0.5 * _unit(delta, DELTA_RANGE) + 0.5 * _unit(rms, FEATURE_RANGE)
    match = round(100 * (1 - distance), 1)
    diffs = [
        Difference(
            name,
            feats[name],
            profile.features[name],
            z,
            _message(name, feats[name], profile.features[name]),
        )
        for name, z in sorted(zs, key=lambda kv: -abs(kv[1]))
        if abs(z) >= 0.5
    ]
    return match, diffs


def _unit(x: float, rng: tuple[float, float]) -> float:
    lo, hi = rng
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def voice_match(text: str, profile: StyleProfile | dict) -> float:
    prof = profile if isinstance(profile, StyleProfile) else StyleProfile(**profile)
    return compare(text, prof)[0]
