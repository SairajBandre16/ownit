"""Fluency language models.

Two implementations of the same `FluencyScorer` protocol:

* `KenLMScorer` - a 5-gram KenLM binary built by scripts/build_lm.py (Docker/Linux).
* `TrigramScorer` - pure-Python/numpy trigram model with stupid backoff, built from the
  same corpus into a compact `.npz` count table. Used when KenLM isn't installed.

Scores are SLOR (syntactic log-odds ratio): the average per-token log10 probability under the
n-gram model minus the average unigram log10 probability. Subtracting the unigram term stops the
score from simply rewarding long, predictable phrases ("in order to", "has the ability to") and
penalising rare-but-correct words. Higher = more fluent.
"""

from __future__ import annotations

import logging
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import numpy as np

from app.config import settings

log = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+(?:[.,]\d+)*|[^\sa-z\d]")
BOS, EOS, UNK = "<s>", "</s>", "<unk>"
BACKOFF = 0.4
SATURATE = -1.0  # log10(0.1)


def tokenize(text: str) -> list[str]:
    """Normalisation shared by the LM builder and the scorers."""
    tokens = TOKEN_RE.findall(text.lower())
    return ["<num>" if t[0].isdigit() else t for t in tokens]


def tokenize_spans(text: str) -> list[tuple[str, int, int]]:
    """Like tokenize(), with character offsets."""
    out = []
    for m in TOKEN_RE.finditer(text.lower()):
        t = m.group()
        out.append(("<num>" if t[0].isdigit() else t, m.start(), m.end()))
    return out


def mean_excluding(contribs: list[tuple[int, int, float]], exclude: list[tuple[int, int]]) -> float:
    """Average per-token SLOR contribution over tokens outside `exclude` spans."""
    vals = [v for s, e, v in contribs if not any(s < xe and xs < e for xs, xe in exclude)]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


class FluencyScorer(Protocol):
    name: str

    @property
    def ready(self) -> bool: ...

    def score(self, text: str) -> float: ...

    def token_scores(self, text: str) -> list[tuple[int, int, float]]: ...

    def token_logprobs(self, text: str) -> list[tuple[int, int, float]]: ...


class KenLMScorer:
    name = "kenlm"

    def __init__(self, path: Path) -> None:
        import kenlm  # type: ignore[import-not-found]

        self._model = kenlm.Model(str(path))

    @property
    def ready(self) -> bool:
        return True

    def score(self, text: str) -> float:
        tokens = tokenize(text)
        if not tokens:
            return 0.0
        lm = float(self._model.score(" ".join(tokens), bos=True, eos=True))
        uni = sum(float(self._model.score(t, bos=False, eos=False)) for t in tokens)
        return (lm - uni) / (len(tokens) + 1)

    def token_scores(self, text: str) -> list[tuple[int, int, float]]:
        spans = tokenize_spans(text)
        if not spans:
            return []
        sentence = " ".join(t for t, _, _ in spans)
        full = list(self._model.full_scores(sentence, bos=True, eos=True))
        out = []
        for (tok, s, e), (lp, _, _) in zip(spans, full, strict=False):
            out.append((s, e, float(lp) - float(self._model.score(tok, bos=False, eos=False))))
        out.append((len(text), len(text), float(full[-1][0])))  # </s>
        return out

    def token_logprobs(self, text: str) -> list[tuple[int, int, float]]:
        spans = tokenize_spans(text)
        if not spans:
            return []
        sentence = " ".join(t for t, _, _ in spans)
        full = list(self._model.full_scores(sentence, bos=True, eos=True))
        offsets = [(s, e) for _, s, e in spans] + [(len(text), len(text))]
        return [(s, e, float(lp)) for (s, e), (lp, _, _) in zip(offsets, full, strict=False)]


class TrigramScorer:
    """Stupid-backoff trigram LM over integer n-gram keys stored in sorted numpy arrays."""

    name = "fallback"

    def __init__(self, path: Path | None = None) -> None:
        self.vocab: dict[str, int] = {}
        self._uni = np.zeros(0, dtype=np.int64)
        self._bi_keys = np.zeros(0, dtype=np.int64)
        self._bi_counts = np.zeros(0, dtype=np.int64)
        self._tri_keys = np.zeros(0, dtype=np.int64)
        self._tri_counts = np.zeros(0, dtype=np.int64)
        self._total = 1
        if path is not None and path.exists():
            self.load(path)

    @property
    def ready(self) -> bool:
        return len(self.vocab) > 0

    # --- persistence -------------------------------------------------------
    def load(self, path: Path) -> None:
        data = np.load(path, allow_pickle=False)
        words = data["vocab"].tolist()
        self.vocab = {w: i for i, w in enumerate(words)}
        self._uni = data["uni"]
        self._bi_keys, self._bi_counts = data["bi_keys"], data["bi_counts"]
        self._tri_keys, self._tri_counts = data["tri_keys"], data["tri_counts"]
        self._total = int(self._uni.sum())

    @staticmethod
    def save(
        path: Path,
        vocab: list[str],
        uni: np.ndarray,
        bi: tuple[np.ndarray, np.ndarray],
        tri: tuple[np.ndarray, np.ndarray],
    ) -> None:
        np.savez_compressed(
            path,
            vocab=np.array(vocab),
            uni=uni,
            bi_keys=bi[0],
            bi_counts=bi[1],
            tri_keys=tri[0],
            tri_counts=tri[1],
        )

    # --- lookup ------------------------------------------------------------
    @staticmethod
    def _lookup(keys: np.ndarray, counts: np.ndarray, key: int) -> int:
        i = int(np.searchsorted(keys, key))
        if i < len(keys) and int(keys[i]) == key:
            return int(counts[i])
        return 0

    def _ids(self, tokens: list[str]) -> list[int]:
        unk = self.vocab[UNK]
        return [self.vocab.get(t, unk) for t in tokens]

    def _logprob(self, u: int, v: int, w: int) -> float:
        n = len(self.vocab)
        c_uv = self._lookup(self._bi_keys, self._bi_counts, u * n + v)
        if c_uv:
            c_uvw = self._lookup(self._tri_keys, self._tri_counts, (u * n + v) * n + w)
            if c_uvw:
                return math.log10(c_uvw / c_uv)
        penalty = math.log10(BACKOFF)
        c_v = int(self._uni[v])
        if c_v:
            c_vw = self._lookup(self._bi_keys, self._bi_counts, v * n + w)
            if c_vw:
                return penalty + math.log10(c_vw / c_v)
        return 2 * penalty + math.log10((int(self._uni[w]) + 1) / (self._total + n))

    def score(self, text: str) -> float:
        tokens = tokenize(text)
        if not tokens or not self.ready:
            return 0.0
        ids = self._ids([BOS, BOS, *tokens, EOS])
        total = sum(self._logprob(ids[i - 2], ids[i - 1], ids[i]) for i in range(2, len(ids)))
        n = len(self.vocab)
        uni = sum(math.log10((int(self._uni[w]) + 1) / (self._total + n)) for w in ids[2:])
        return (total - uni) / (len(ids) - 2)

    def token_scores(self, text: str) -> list[tuple[int, int, float]]:
        spans = tokenize_spans(text)
        if not spans or not self.ready:
            return []
        ids = self._ids([BOS, BOS, *(t for t, _, _ in spans), EOS])
        n = len(self.vocab)
        offsets = [(s, e) for _, s, e in spans] + [(len(text), len(text))]
        out = []
        for i in range(2, len(ids)):
            w = ids[i]
            lp = self._logprob(ids[i - 2], ids[i - 1], w)
            uni = math.log10((int(self._uni[w]) + 1) / (self._total + n))
            s, e = offsets[i - 2]
            out.append((s, e, lp - uni))
        return out

    def token_logprobs(self, text: str) -> list[tuple[int, int, float]]:
        spans = tokenize_spans(text)
        if not spans or not self.ready:
            return []
        ids = self._ids([BOS, BOS, *(t for t, _, _ in spans), EOS])
        offsets = [(s, e) for _, s, e in spans] + [(len(text), len(text))]
        return [
            (*offsets[i - 2], self._logprob(ids[i - 2], ids[i - 1], ids[i]))
            for i in range(2, len(ids))
        ]


class CachedScorer:
    """Memoises sentence scores (the ranker scores the same original many times)."""

    def __init__(self, inner: KenLMScorer | TrigramScorer) -> None:
        self.inner = inner
        self.name = inner.name
        self._score = lru_cache(maxsize=65536)(inner.score)
        self._tokens = lru_cache(maxsize=16384)(inner.token_scores)
        self._logprobs = lru_cache(maxsize=16384)(inner.token_logprobs)

    @property
    def ready(self) -> bool:
        return self.inner.ready

    def score(self, text: str) -> float:
        return self._score(text)

    def token_scores(self, text: str) -> list[tuple[int, int, float]]:
        return self._tokens(text)

    def token_logprobs(self, text: str) -> list[tuple[int, int, float]]:
        return self._logprobs(text)


@lru_cache(maxsize=1)
def get_fluency_scorer() -> CachedScorer:
    lm_dir = settings.lm_dir
    kenlm_path = lm_dir / "wiki5.binary"
    if kenlm_path.exists():
        try:
            return CachedScorer(KenLMScorer(kenlm_path))
        except ImportError:
            log.info("kenlm not installed, using fallback trigram LM")
    fallback = lm_dir / "trigram.npz"
    if not fallback.exists():
        log.warning("No LM found at %s - fluency scores will be neutral", fallback)
    return CachedScorer(TrigramScorer(fallback))


def fluency_norm(orig_score: float, cand_score: float) -> float:
    """Map a candidate's fluency relative to the original onto [0, 1].

    Scores are mean log10 probabilities of the same (unchanged) tokens; 0.5 means equal,
    and a change of ±1 log10 per token (10x more/less likely) moves it to 1 or 0.
    """
    return max(0.0, min(1.0, 0.5 + 0.5 * (cand_score - orig_score)))


def fluency_drop(orig_score: float, cand_score: float) -> float:
    """Relative drop in mean log-probability (negative numbers); 0.15 = 15 % worse."""
    if cand_score >= orig_score or orig_score >= 0:
        return 0.0
    return (orig_score - cand_score) / abs(orig_score)


def unchanged_mean(
    tokens: list[tuple[int, int, float]], changed: list[tuple[int, int]]
) -> tuple[float, int]:
    """Mean log-prob of tokens that don't overlap `changed` spans (+ how many there were).

    Log-probs saturate at SATURATE (p >= 0.1 counts as fully natural), so a deleted lead-in
    that made the next word near-certain ("in order -> to") doesn't count as lost fluency.
    """
    vals = [
        min(v, SATURATE)
        for s, e, v in tokens
        if not any((s < ce and cs < e) or (s == e and cs <= s < ce) for cs, ce in changed)
    ]
    return (sum(vals) / len(vals), len(vals)) if vals else (0.0, 0)


NOISE_MARGIN = 1.0  # log10: per-token changes smaller than 10x are within n-gram noise


def _outside(tokens: list[tuple[int, int, float]], changed: list[tuple[int, int]]) -> list[float]:
    return [
        min(v, SATURATE)
        for s, e, v in tokens
        if not any((s < ce and cs < e) or (s == e and cs <= s < ce) for cs, ce in changed)
    ]


def paired_delta(
    orig_tokens: list[tuple[int, int, float]],
    old_spans: list[tuple[int, int]],
    cand_tokens: list[tuple[int, int, float]],
    new_spans: list[tuple[int, int]],
) -> tuple[float, float, int]:
    """Compare the tokens a rewrite kept, pairwise, in their old vs new context.

    Returns (original mean log-prob, mean per-token change, number of tokens). Each change is
    soft-thresholded by NOISE_MARGIN so only real disruptions (or real gains) count.
    """
    a = _outside(orig_tokens, old_spans)
    b = _outside(cand_tokens, new_spans)
    n = min(len(a), len(b))
    if n < len(orig_tokens) / 2:
        # the rewrite replaced most of the sentence: compare whole-sentence means instead
        a = [min(v, SATURATE) for _, _, v in orig_tokens]
        b = [min(v, SATURATE) for _, _, v in cand_tokens]
        if not a or not b:
            return 0.0, 0.0, 0
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        d = mb - ma
        margin = NOISE_MARGIN / 3
        soft = (abs(d) - margin) * (1 if d > 0 else -1) if abs(d) > margin else 0.0
        return ma, soft, len(a)
    deltas = []
    for x, y in zip(a[:n], b[:n], strict=True):
        d = y - x
        deltas.append(
            (abs(d) - NOISE_MARGIN) * (1 if d > 0 else -1) if abs(d) > NOISE_MARGIN else 0.0
        )
    return sum(a[:n]) / n, sum(deltas) / n, n
