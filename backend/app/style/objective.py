"""Fast, incremental Voice Match objective for the humanizer (U1).

Recomputing the full fingerprint for every candidate would need a parse per candidate, so this
keeps running document totals of parse-free approximations of the fingerprint features
(function-word counts, word/sentence lengths, punctuation, contractions, first person,
transitions, word-frequency tiers, sentence-opener classes, passive voice) and scores a
candidate by how much swapping it in moves the document towards the student's profile.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from app.core.nlp import zipf
from app.humanize.transforms.transition_vary import opening_transition
from app.style.delta import DELTA_RANGE, FEATURE_RANGE, FEATURE_SCALE, PRIOR_WORDS, _unit
from app.style.fingerprint import CONTRACTION_RE, FIRST_PERSON, function_words

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(])")
PASSIVE_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?\w+(?:ed|en|wn|lt|ught)\b", re.IGNORECASE
)

# cheap sentence-opener classes (match the POS classes used by the fingerprint)
OPENER_CLASS = {
    **dict.fromkeys(
        [
            "the",
            "a",
            "an",
            "this",
            "these",
            "that",
            "those",
            "each",
            "every",
            "some",
            "any",
            "no",
            "all",
            "both",
        ],
        "DET",
    ),
    **dict.fromkeys(["it", "we", "i", "they", "he", "she", "you", "there", "one"], "PRON"),
    **dict.fromkeys(
        [
            "in",
            "on",
            "at",
            "for",
            "during",
            "after",
            "before",
            "with",
            "by",
            "from",
            "to",
            "of",
            "under",
            "over",
            "within",
            "through",
            "throughout",
            "without",
            "as",
            "like",
        ],
        "ADP",
    ),
    **dict.fromkeys(
        [
            "because",
            "when",
            "although",
            "though",
            "if",
            "while",
            "since",
            "once",
            "unless",
            "whenever",
            "whereas",
        ],
        "SCONJ",
    ),
    **dict.fromkeys(["and", "but", "or", "so", "yet", "nor"], "CCONJ"),
}
ADVERB_OPENERS = {
    "however",
    "also",
    "moreover",
    "furthermore",
    "then",
    "finally",
    "therefore",
    "thus",
    "hence",
    "additionally",
    "consequently",
    "today",
    "now",
    "first",
    "firstly",
    "next",
    "later",
    "similarly",
    "instead",
    "still",
    "overall",
    "currently",
    "recently",
}
OPENERS = ("DET", "PRON", "ADP", "ADV", "SCONJ", "NOUN")
TIERS = ("zipf_lt3", "zipf_3_4", "zipf_4_5", "zipf_gt5")
FAST_FEATURES = (
    "sentence_length_mean",
    "sentence_length_sd",
    "word_length_mean",
    "commas_per_sentence",
    "semicolons_per_sentence",
    "colons_per_sentence",
    "parentheses_per_sentence",
    "questions_per_sentence",
    "contractions_per_sentence",
    "first_person_per_1000",
    "transitions_per_sentence",
    "passive_ratio",
    *TIERS,
    *(f"opener_{o}" for o in OPENERS),
)


def opener_class(sentence: str) -> str:
    m = WORD_RE.search(sentence)
    if not m:
        return "OTHER"
    w = m.group().lower()
    if w in OPENER_CLASS:
        return OPENER_CLASS[w]
    if w in ADVERB_OPENERS or w.endswith("ly"):
        return "ADV"
    return "NOUN"


def _tier(word: str) -> str:
    z = zipf(word)
    return TIERS[0] if z < 3 else TIERS[1] if z < 4 else TIERS[2] if z < 5 else TIERS[3]


@dataclass
class SentenceStats:
    words: int = 0
    letters: int = 0
    lengths: tuple[int, ...] = ()
    counts: Counter[str] = field(default_factory=Counter)  # punctuation, tiers, openers, ...
    fw: Counter[str] = field(default_factory=Counter)


def sentence_stats(text: str) -> SentenceStats:
    parts = [p for p in SPLIT_RE.split(text) if p.strip()] or [text]
    words = WORD_RE.findall(text)
    lower = [w.lower() for w in words]
    fw_set = set(function_words()["words"])  # type: ignore[arg-type]
    counts: Counter[str] = Counter()
    counts["commas"] = text.count(",")
    counts["semicolons"] = text.count(";")
    counts["colons"] = len(re.findall(r"(?<!\d):(?!\d)", text))
    counts["parentheses"] = text.count("(")
    counts["questions"] = text.count("?")
    counts["contractions"] = len(CONTRACTION_RE.findall(text))
    counts["first_person"] = sum(1 for w in lower if w in FIRST_PERSON)
    for p in parts:
        counts["transitions"] += 1 if opening_transition(p) else 0
        counts["passive"] += 1 if PASSIVE_RE.search(p) else 0
        counts[f"opener_{opener_class(p)}"] += 1
    for w in lower:
        counts[_tier(w)] += 1
    return SentenceStats(
        words=len(words),
        letters=sum(len(w) for w in words),
        lengths=tuple(len(WORD_RE.findall(p)) for p in parts),
        counts=counts,
        fw=Counter(w for w in lower if w in fw_set),
    )


class VoiceObjective:
    def __init__(self, profile: dict, sentences: list[str]) -> None:
        self.profile_feats: dict[str, float] = profile.get("features", {})
        self.profile_fw: dict[str, float] = profile.get("function_word_freqs", {})
        self.stats = [sentence_stats(s) for s in sentences]
        self._recount()
        self._cache: dict[tuple[int, str], float] = {}

    def _recount(self) -> None:
        self.n_words = sum(x.words for x in self.stats)
        self.letters = sum(x.letters for x in self.stats)
        self.counts: Counter[str] = Counter()
        self.fw: Counter[str] = Counter()
        self.lengths: list[int] = []
        for x in self.stats:
            self.counts.update(x.counts)
            self.fw.update(x.fw)
            self.lengths.extend(n for n in x.lengths if n)
        self._current = self._distance(
            self.n_words, self.letters, self.counts, self.fw, self.lengths
        )

    def _distance(
        self, n_words: int, letters: int, counts: Counter[str], fw: Counter[str], lengths: list[int]
    ) -> float:
        ref = function_words()
        n = max(n_words, 1)
        n_s = max(len(lengths), 1)
        weight = n / (n + PRIOR_WORDS)
        words = ref["words"]
        total = 0.0
        for w in words:  # type: ignore[union-attr]
            mean, sd = ref["mean"][w], ref["sd"][w]  # type: ignore[index]
            rate = weight * (1000 * fw[w] / n) + (1 - weight) * mean
            total += abs((rate - self.profile_fw.get(w, 0.0)) / sd)
        delta = total / len(words)  # type: ignore[arg-type]
        mean_len = sum(lengths) / n_s if lengths else 0.0
        sd_len = (
            math.sqrt(sum((x - mean_len) ** 2 for x in lengths) / n_s) if len(lengths) > 1 else 0.0
        )
        feats = {
            "sentence_length_mean": mean_len,
            "sentence_length_sd": sd_len,
            "word_length_mean": letters / n,
            "commas_per_sentence": counts["commas"] / n_s,
            "semicolons_per_sentence": counts["semicolons"] / n_s,
            "colons_per_sentence": counts["colons"] / n_s,
            "parentheses_per_sentence": counts["parentheses"] / n_s,
            "questions_per_sentence": counts["questions"] / n_s,
            "contractions_per_sentence": counts["contractions"] / n_s,
            "first_person_per_1000": 1000 * counts["first_person"] / n,
            "transitions_per_sentence": counts["transitions"] / n_s,
            "passive_ratio": counts["passive"] / n_s,
            **{t: counts[t] / n for t in TIERS},
            **{f"opener_{o}": counts[f"opener_{o}"] / n_s for o in OPENERS},
        }
        zs = [
            (feats[k] - self.profile_feats[k]) / FEATURE_SCALE[k]
            for k in FAST_FEATURES
            if k in self.profile_feats and k in FEATURE_SCALE
        ]
        rms = math.sqrt(sum(z * z for z in zs) / len(zs)) if zs else 0.0
        return 0.5 * _unit(delta, DELTA_RANGE) + 0.5 * _unit(rms, FEATURE_RANGE)

    def current(self) -> float:
        return self._current

    def distance_if(self, index: int, new_text: str) -> float:
        """Document distance if sentence `index` were replaced by `new_text`."""
        key = (index, new_text)
        if key in self._cache:
            return self._cache[key]
        old, new = self.stats[index], sentence_stats(new_text)
        counts = self.counts - old.counts
        counts.update(new.counts)
        fw = self.fw - old.fw
        fw.update(new.fw)
        lengths = list(self.lengths)
        for n in old.lengths:
            if n in lengths:
                lengths.remove(n)
        lengths += [n for n in new.lengths if n]
        d = self._distance(
            self.n_words - old.words + new.words,
            self.letters - old.letters + new.letters,
            counts,
            fw,
            lengths,
        )
        self._cache[key] = d
        return d

    def gain(self, index: int, new_text: str) -> float:
        """Positive = the candidate moves the document towards the student's voice."""
        return self._current - self.distance_if(index, new_text)

    def commit(self, index: int, new_text: str) -> None:
        self.stats[index] = sentence_stats(new_text)
        self._recount()
        self._cache.clear()
