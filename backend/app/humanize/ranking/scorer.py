"""Candidate scoring and hard gates (CLAUDE.md §6.3).

score = 0.35·fluency_norm + 0.30·meaning_sim + 0.15·style_fit − 0.20·grammar_penalty

Hard gates (reject): meaning_sim < 0.80, new grammar errors > 0, fluency drop > 15 %.
Candidates never touch protected spans (enforced when they are built).
"""

from __future__ import annotations

from app.humanize.ranking.fluency import (
    fluency_drop,
    fluency_norm,
    get_fluency_scorer,
    paired_delta,
)
from app.humanize.ranking.meaning import candidate_tokens, meaning_sim_fast
from app.humanize.ranking.style_fit import StyleTargets, lexicon_hits, style_fit
from app.humanize.types import Candidate

W_FLUENCY, W_MEANING, W_STYLE, W_GRAMMAR = 0.35, 0.30, 0.15, 0.20
MEANING_GATE = 0.80
FLUENCY_DROP_GATE = 0.15
# Minimum score gain over the original required to accept a rewrite, by intensity.
# The original always has meaning_sim = 1 and fluency_norm = 0.5, so any rewrite pays a small
# meaning cost; higher intensities tolerate a slightly lower total as long as every hard gate
# (meaning, grammar, fluency drop, protected spans) still passes.
MIN_IMPROVEMENT = {1: 0.0, 2: -0.01, 3: -0.02, 4: -0.03, 5: -0.04}


def total(c: Candidate) -> float:
    grammar_penalty = min(1.0, float(c.grammar_new))
    return (
        W_FLUENCY * c.fluency_norm
        + W_MEANING * c.meaning
        + W_STYLE * c.style
        - W_GRAMMAR * grammar_penalty
    )


def score_candidates(
    original: Candidate,
    cands: list[Candidate],
    orig_doc,  # type: ignore[no-untyped-def]
    targets: StyleTargets,
) -> None:
    """Fill fluency/meaning/style/score for the original and each candidate (in place)."""
    lm = get_fluency_scorer()
    orig_f = lm.score(original.text)
    original.fluency, original.fluency_norm, original.meaning = orig_f, 0.5, 1.0
    original.style = style_fit(original.text, _words(original.text), targets)
    original.score = total(original)
    orig_tokens = lm.token_logprobs(original.text) if lm.ready else []
    for c in cands:
        c.fluency = lm.score(c.text)
        toks = candidate_tokens(
            orig_doc, c.text, [(e.start, e.end, len(e.replacement)) for e in c.edits]
        )
        c.meaning = meaning_sim_fast(orig_doc, toks, empty_phrase_lemmas(c, orig_doc))
        c.style = style_fit(c.text, _words(c.text), targets)
        if lm.ready:
            # Fluency of the words the rewrite kept, read in their old vs. new context: a bad
            # edit makes its neighbours improbable. (Whole-sentence averages would reward
            # predictable stock phrases, and SLOR would punish plain words like "use".)
            old_spans, new_spans = edit_spans(c)
            ref, delta, n = paired_delta(
                orig_tokens, old_spans, lm.token_logprobs(c.text), new_spans
            )
            c.fluency_norm = fluency_norm(ref, ref + delta) if n else 0.5
            drop = fluency_drop(ref, ref + delta) if n else 0.0
        else:
            c.fluency_norm, drop = 0.5, 0.0
        c.score = total(c)
        if c.meaning < MEANING_GATE:
            c.rejected = "meaning"
        elif drop > FLUENCY_DROP_GATE:
            c.rejected = "fluency"


def edit_spans(c: Candidate) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Edited spans in the original sentence and in the candidate text."""
    old, new = [], []
    delta = 0
    for e in sorted(c.edits, key=lambda e: e.start):
        old.append((e.start, e.end))
        ns = e.start + delta
        # a pure deletion still "changes" the position where it happened
        new.append((ns, ns + max(len(e.replacement), 0)))
        delta += len(e.replacement) - (e.end - e.start)
    return old, new


PHRASE_TRANSFORMS = ("phrase_simplify", "transition_vary")


def empty_phrase_lemmas(c: Candidate, orig_doc) -> frozenset[str]:  # type: ignore[no-untyped-def]
    """Lemmas inside lexicon phrases this candidate removed or condensed."""
    out: set[str] = set()
    for e in c.edits:
        if e.transform not in PHRASE_TRANSFORMS:
            continue
        new_words = {w.lower().strip(".,;:") for w in e.replacement.split()}
        for tok in orig_doc:
            if e.start <= tok.idx < e.end and tok.lower_ not in new_words:
                out.add(tok.lemma_.lower())
    return frozenset(out)


def apply_grammar(original_errors: int, c: Candidate, new_errors: int) -> None:
    c.grammar_new = new_errors
    c.score = total(c)
    if new_errors > 0 and c.rejected is None:
        c.rejected = "grammar"


def choose(
    original: Candidate, cands: list[Candidate], intensity: int, prefer: str = "score"
) -> Candidate:
    """Best surviving candidate if it beats the original by the intensity's margin."""
    ok = [c for c in cands if c.rejected is None]
    if not ok:
        return original
    if prefer == "simplest":
        return min(ok, key=lambda c: (lexicon_hits(c.text), len(c.text.split()), -c.score))
    best = max(ok, key=lambda c: c.score)
    if best.score >= original.score + MIN_IMPROVEMENT.get(intensity, 0.0):
        return best
    return original


def ranked(original: Candidate, cands: list[Candidate], intensity: int) -> list[Candidate]:
    """Accepted alternatives, best first (used by the document pass)."""
    margin = MIN_IMPROVEMENT.get(intensity, 0.0)
    ok = [c for c in cands if c.rejected is None and c.score >= original.score + margin]
    return sorted(ok, key=lambda c: -c.score)


def confidence(c: Candidate) -> float:
    m = max(0.0, min(1.0, (c.meaning - MEANING_GATE) / (1 - MEANING_GATE)))
    return round(max(0.05, min(0.99, 0.25 + 0.45 * m + 0.3 * c.fluency_norm)), 2)


def _words(text: str) -> int:
    return sum(1 for w in text.split() if any(ch.isalnum() for ch in w))
