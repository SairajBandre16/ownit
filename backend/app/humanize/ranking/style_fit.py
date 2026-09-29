"""style_fit: closeness of a sentence to style targets (tone + the student's voice, U1).

Components (each 0-1):
  cleanliness  fewer wordy/stock/filler/weak-verb/cliché hits
  length_fit   sentence length near the target for the tone or the student's profile
  tone_fit     contractions and casual/formal transitions match the tone (or the profile)
  plainness    content words are common rather than rare
  voice        (only with a profile) function-word and punctuation habits close to the student's
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache

from app.core.lexicon import lexicon
from app.core.nlp import zipf

LENGTH_TARGET = {"academic": (21.0, 8.0), "neutral": (17.0, 7.0), "casual": (14.0, 6.0)}
CONTRACTION_RE = re.compile(r"\b\w+(?:n't|'re|'ve|'ll|'d|'m|'s)\b", re.IGNORECASE)
CASUAL_OPENERS = re.compile(r"^\s*(so|anyway|plus|but|and|also|actually|really)\b", re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


@dataclass
class StyleTargets:
    tone: str = "academic"
    length_mean: float | None = None
    length_sd: float | None = None
    contraction_rate: float | None = None  # per sentence, from a voice profile
    function_word_freqs: dict[str, float] | None = None  # per 1000 words, from a voice profile
    comma_rate: float | None = None
    dash_rate: float | None = None  # dashes per sentence in the student's own writing
    recent_openers: tuple[str, ...] = ()  # first words of the previous sentences


@lru_cache(maxsize=1)
def _lexicons():  # type: ignore[no-untyped-def]
    return [
        lexicon(n)
        for n in ("wordy_phrases", "ai_style_phrases", "fillers", "weak_verbs", "cliches")
    ]


def dash_hits(text: str, t: StyleTargets) -> int:
    """Dashes used as sentence punctuation, unless dashes are part of the student's voice."""
    from app.humanize.transforms.dash_tidy import OWN_STYLE_RATE, dashes

    if t.dash_rate is not None and t.dash_rate >= OWN_STYLE_RATE:
        return 0
    return len(dashes(text))


def lexicon_hits(text: str) -> int:
    n = 0
    for lx in _lexicons():
        for m in lx.find(text):
            v = m.value
            if isinstance(v, dict) or v is not None:
                n += 1
    return n


def length_fit(words: int, t: StyleTargets) -> float:
    mean, sd = LENGTH_TARGET.get(t.tone, LENGTH_TARGET["neutral"])
    if t.length_mean:
        mean, sd = t.length_mean, max(4.0, t.length_sd or sd)
    z = (words - mean) / (sd * 1.5)
    return math.exp(-0.5 * z * z)


def tone_fit(text: str, t: StyleTargets) -> float:
    contractions = len(CONTRACTION_RE.findall(text))
    casual_open = bool(CASUAL_OPENERS.match(text))
    if t.contraction_rate is not None:
        want = t.contraction_rate  # expected contractions per sentence
        c = 1.0 - min(1.0, abs(contractions - want) / 2)
        return 0.7 * c + 0.3 * (
            1.0 if (casual_open and t.tone == "casual") or not casual_open else 0.5
        )
    if t.tone == "academic":
        return 1.0 - min(1.0, 0.5 * contractions + (0.3 if casual_open else 0.0))
    if t.tone == "casual":
        return min(1.0, 0.6 + 0.2 * contractions)
    return 1.0 - min(0.5, 0.2 * contractions)


def plainness(text: str) -> float:
    words = [w.lower() for w in WORD_RE.findall(text) if len(w) > 3]
    if not words:
        return 0.5
    mean = sum(zipf(w) for w in words) / len(words)
    return max(0.0, min(1.0, (mean - 3.0) / 2.5))


def voice_fit(text: str, t: StyleTargets) -> float | None:
    if not t.function_word_freqs:
        return None
    words = [w.lower() for w in WORD_RE.findall(text)]
    if not words:
        return None
    # how many of the student's frequent function words appear, vs. rare-for-them ones
    fav = {w for w, f in t.function_word_freqs.items() if f >= 8.0}
    rare = {w for w, f in t.function_word_freqs.items() if f < 1.0}
    uses_fav = sum(1 for w in words if w in fav)
    uses_rare = sum(1 for w in words if w in rare)
    score = (
        0.6 + 0.4 * min(1.0, uses_fav / max(1, len(words) * 0.35)) - 0.3 * min(1.0, uses_rare / 3)
    )
    if t.comma_rate is not None:
        commas = text.count(",")
        score -= 0.1 * min(1.0, abs(commas - t.comma_rate) / 3)
    return max(0.0, min(1.0, score))


SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(])")


def sentence_lengths(text: str) -> list[int]:
    return [
        len([w for w in part.split() if any(c.isalnum() for c in w)])
        for part in SENT_END.split(text)
    ]


def style_fit(text: str, words: int, t: StyleTargets) -> float:
    # each flagged phrase (or dash) halves cleanliness: removing one is a clear, measurable gain
    cleanliness = 0.5 ** (lexicon_hits(text) + dash_hits(text, t))
    lengths = sentence_lengths(text) or [words]
    len_fit = sum(length_fit(n, t) for n in lengths) / len(lengths)
    parts = [
        (0.45, cleanliness),
        (0.25, len_fit),
        (0.15, tone_fit(text, t)),
        (0.15, plainness(text)),
    ]
    if t.recent_openers:
        first = text.split(" ", 1)[0].strip(",").lower()
        repeats = sum(1 for o in t.recent_openers[-3:] if o == first)
        parts.append((0.1, 1.0 if repeats == 0 else 0.5 if repeats == 1 else 0.0))
    v = voice_fit(text, t)
    if v is not None:
        parts = [(w * 0.75, s) for w, s in parts] + [(0.25, v)]
    return sum(w * s for w, s in parts) / sum(w for w, _ in parts)
