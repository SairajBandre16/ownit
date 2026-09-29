"""Core types for the humanize engine.

A sentence is rewritten by *edits* on its original text (never on a re-parsed rewrite), so
every change keeps exact offsets and its own reason. A candidate is a set of non-overlapping
edits; chaining two transforms means taking the union of their edits.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from spacy.tokens import Span, Token

from app.core.segment import Segmentation, Sentence
from app.core.spans import Edit, SpanIndex, apply_edits

CATEGORY_BY_TRANSFORM = {
    "phrase_simplify": "clarity",
    "synonym": "vocabulary",
    "transition_vary": "rhythm",
    "split_long": "clarity",
    "merge_short": "rhythm",
    "passive_to_active": "voice",
    "clause_front": "rhythm",
    "opener_vary": "rhythm",
    "contractions": "voice",
    "voice_fit": "voice",
    "dash_tidy": "clarity",
}


@dataclass(frozen=True)
class LocalEdit:
    """An edit relative to the sentence text, with its explanation."""

    start: int
    end: int
    replacement: str
    transform: str
    reason: str
    category: str

    def overlaps(self, other: LocalEdit) -> bool:
        # touching edits also conflict (e.g. both would capitalise the same word)
        return self.start <= other.end and other.start <= self.end


@dataclass
class Candidate:
    edits: tuple[LocalEdit, ...]
    transforms: tuple[str, ...]
    text: str = ""
    # filled in by the ranker
    fluency: float = 0.0
    fluency_norm: float = 0.5
    meaning: float = 1.0
    style: float = 0.0
    grammar_new: int = 0
    score: float = 0.0
    rejected: str | None = None

    @property
    def is_original(self) -> bool:
        return not self.edits


# transforms that reorder a sentence: they may move protected text, never change it
RESTRUCTURING = {"passive_to_active", "clause_front", "opener_vary", "merge_short"}


def make_candidate(
    view: SentenceView, edits: list[LocalEdit], transforms: tuple[str, ...]
) -> Candidate | None:
    """Build a candidate; returns None if edits overlap each other or a protected span."""
    ordered = sorted(edits, key=lambda e: (e.start, e.end))
    for a, b in itertools.pairwise(ordered):
        if a.overlaps(b):
            return None
    for e in ordered:
        if view.touches_protected(e.start, e.end) and not (
            e.transform in RESTRUCTURING and view.moves_protected_intact(e)
        ):
            return None
    text = apply_edits(view.text, [Edit(e.start, e.end, e.replacement) for e in ordered])
    if text == view.text:
        return None
    return Candidate(edits=tuple(ordered), transforms=transforms, text=text)


def combine(view: SentenceView, a: Candidate, b: Candidate) -> Candidate | None:
    return make_candidate(
        view, [*a.edits, *b.edits], tuple(dict.fromkeys(a.transforms + b.transforms))
    )


@dataclass
class SentenceView:
    """A body sentence being rewritten."""

    sentence: Sentence
    protected: SpanIndex  # local offsets

    @property
    def text(self) -> str:
        return self.sentence.text

    @property
    def span(self) -> Span:
        return self.sentence.span

    @property
    def start(self) -> int:
        return self.sentence.start

    def local(self, tok: Token) -> tuple[int, int]:
        s = tok.idx - self.start
        return s, s + len(tok.text)

    def touches_protected(self, start: int, end: int) -> bool:
        return self.protected.overlaps(start, end)

    def moves_protected_intact(self, e: LocalEdit) -> bool:
        """Every protected span touched by the edit lies fully inside it and reappears
        byte-identical in the replacement (so the edit only moves protected text)."""
        spans = self.protected.spans_in(e.start, e.end)
        needed: dict[str, int] = {}
        for s, t in spans:
            # spans_in clips to the window: a clipped span crosses the edit boundary
            if not self.protected.covered(s, t) or s < e.start or t > e.end:
                return False
            full = [(a, b) for a, b in self.protected.spans_in(s, t)]
            if full != [(s, t)]:
                return False
            piece = self.text[s:t]
            needed[piece] = needed.get(piece, 0) + 1
        for piece, n in needed.items():
            if e.replacement.count(piece) < n:
                return False
        # the protected span must not have been clipped at the window edges
        return all(not self._span_extends_outside(s, t, e) for s, t in spans)

    def _span_extends_outside(self, s: int, t: int, e: LocalEdit) -> bool:
        before = self.protected.overlaps(max(0, s - 1), s) and s == e.start
        after = self.protected.overlaps(t, t + 1) and t == e.end
        return before or after

    def token_protected(self, tok: Token) -> bool:
        s, e = self.local(tok)
        return self.protected.overlaps(s, e)

    @property
    def words(self) -> int:
        return self.sentence.words


@dataclass
class HumanizeContext:
    seg: Segmentation
    protected: SpanIndex  # document offsets
    tone: str = "academic"
    intensity: int = 3
    profile: Any = None  # StyleProfile features (U1)
    # state carried across sentences while rewriting in order
    chosen: list[str] = field(default_factory=list)  # final text of previous sentences
    chosen_openers: list[str] = field(
        default_factory=list
    )  # sentence-initial transition (lowercase) or ""
    swapped_lemmas: dict[int, set[str]] = field(default_factory=dict)  # paragraph -> lemmas swapped
    recent_lemmas: list[set[str]] = field(
        default_factory=list
    )  # content lemmas of previous sentences

    def view(self, sent: Sentence) -> SentenceView:
        local = [
            (s - sent.start, e - sent.start)
            for s, e in self.protected.spans_in(sent.start, sent.end)
        ]
        return SentenceView(sent, SpanIndex(local))
