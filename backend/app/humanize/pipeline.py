"""Humanize pipeline: generate candidates per sentence, rank with gates, assemble changes."""

from __future__ import annotations

import hashlib
import itertools
import time
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

from app.core.protect import Protected, detect_protected
from app.core.segment import Sentence, segment
from app.core.spans import SpanIndex
from app.humanize.docpass import document_pass
from app.humanize.ranking import grammar
from app.humanize.ranking.meaning import content_lemmas
from app.humanize.ranking.scorer import (
    apply_grammar,
    choose,
    confidence,
    edit_spans,
    score_candidates,
    total,
)
from app.humanize.ranking.style_fit import StyleTargets
from app.humanize.transforms import (
    clause_front,
    contractions,
    opener_vary,
    passive_to_active,
    phrase_simplify,
    split_long,
    synonym,
    transition_vary,
    voice_fit,
)
from app.humanize.transforms.transition_vary import opening_transition
from app.humanize.types import (
    CATEGORY_BY_TRANSFORM,
    Candidate,
    HumanizeContext,
    SentenceView,
    combine,
)
from app.style.objective import VoiceObjective

MAX_CANDIDATES = 8
GRAMMAR_CHECK_TOP = 3

# transforms enabled at each intensity (1 = gentlest)
_GENTLE = [phrase_simplify, transition_vary, voice_fit]
_STRUCTURAL = [passive_to_active, clause_front, opener_vary]
TRANSFORMS: dict[int, list[ModuleType]] = {
    1: _GENTLE,
    2: [*_GENTLE, synonym, contractions],
    3: [*_GENTLE, synonym, contractions, split_long, opener_vary],
    4: [*_GENTLE, synonym, contractions, split_long, *_STRUCTURAL],
    5: [*_GENTLE, synonym, contractions, split_long, *_STRUCTURAL],
}


@dataclass
class ChangeRecord:
    id: str
    orig_start: int
    orig_end: int
    new_start: int
    new_end: int
    original: str
    replacement: str
    transform: str
    category: str
    reason: str
    confidence: float


@dataclass
class SentenceResult:
    sentence: Sentence
    view: SentenceView
    original: Candidate
    candidates: list[Candidate]
    chosen: Candidate
    rewritable: bool = True


@dataclass
class HumanizeOutput:
    text: str
    changes: list[ChangeRecord]
    protected: list[Protected]
    sentences: list[SentenceResult] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def _rewritable(sent: Sentence, view: SentenceView, heading_paras: set[int]) -> bool:
    if sent.paragraph in heading_paras or sent.section == "references":
        return False
    if sent.words < 3:
        return False
    protected_chars = sum(e - s for s, e in view.protected.spans_in(0, len(view.text)))
    return protected_chars / max(len(view.text), 1) < 0.6


def generate(
    view: SentenceView, ctx: HumanizeContext, transforms: list[ModuleType]
) -> list[Candidate]:
    singles: list[Candidate] = []
    for t in transforms:
        try:
            singles.extend(t.apply(view, ctx))
        except Exception:
            import logging

            logging.getLogger(__name__).exception("transform %s failed", t.__name__)
    # chains: combine the first (fullest) candidate of each transform, pairwise
    firsts: dict[str, Candidate] = {}
    for c in singles:
        firsts.setdefault(c.transforms[0], c)
    chains = []
    for a, b in itertools.combinations(firsts.values(), 2):
        combo = combine(view, a, b)
        if combo:
            chains.append(combo)
    seen: set[str] = {view.text}
    out: list[Candidate] = []
    for c in [*chains, *singles]:
        if c.text in seen:
            continue
        seen.add(c.text)
        out.append(c)
        if len(out) >= MAX_CANDIDATES - 1:
            break
    return out


def targets_for(tone: str, profile: dict[str, Any] | None) -> StyleTargets:
    t = StyleTargets(tone=tone)
    if profile:
        feats = profile.get("features", {})
        t.length_mean = feats.get("sentence_length_mean")
        t.length_sd = feats.get("sentence_length_sd")
        if "contractions_per_sentence" in feats:
            t.contraction_rate = feats["contractions_per_sentence"]
        if "commas_per_sentence" in feats:
            t.comma_rate = feats["commas_per_sentence"]
        t.function_word_freqs = profile.get("function_word_freqs") or None
    return t


def humanize(
    text: str,
    tone: str = "academic",
    intensity: int = 3,
    keep_terms: tuple[str, ...] = (),
    profile: dict[str, Any] | None = None,
    prefer: str = "score",
) -> HumanizeOutput:
    """`prefer="simplest"` picks, among candidates that pass every gate, the one with the
    fewest stock/wordy phrases and words (used for the Walkthrough's simplified view)."""
    t0 = time.perf_counter()
    seg = segment(text)
    protected = detect_protected(text, tuple(keep_terms))
    index = SpanIndex((p.start, p.end) for p in protected)
    ctx = HumanizeContext(seg=seg, protected=index, tone=tone, intensity=intensity, profile=profile)
    transforms = TRANSFORMS[intensity]
    if profile is not None:
        from app.style.fingerprint import favourite_transitions

        profile = {**profile, "_favourite_transitions": favourite_transitions(profile)}
        ctx.profile = profile
    targets = targets_for(tone, profile)
    heading_paras = {p.index for p in seg.paragraphs if p.is_heading}

    results: list[SentenceResult] = []
    n_candidates = 0
    voice = VoiceObjective(profile, [s.text for s in seg.sentences]) if profile else None
    for si, sent in enumerate(seg.sentences):
        view = ctx.view(sent)
        original = Candidate(edits=(), transforms=(), text=sent.text)
        if not _rewritable(sent, view, heading_paras):
            results.append(SentenceResult(sent, view, original, [], original, rewritable=False))
            continue
        cands = generate(view, ctx, transforms)
        n_candidates += len(cands)
        targets.recent_openers = tuple(
            t.split(" ", 1)[0].strip(",").lower() for t in ctx.chosen[-3:]
        )
        score_candidates(original, cands, sent.span.as_doc(), targets)
        if voice is not None:
            apply_voice(voice, si, original, cands)
        provisional = choose(original, cands, intensity, prefer)
        results.append(SentenceResult(sent, view, original, cands, provisional))
        _advance(ctx, sent, view, provisional)
        if voice is not None:
            voice.commit(si, provisional.text)

    lt_on = grammar.available()
    if lt_on:
        grammar_pass(results, intensity, prefer)

    if intensity >= 3:
        document_pass(results, ctx, intensity, targets)
    if voice is not None:
        voice_revert_pass(results, profile, intensity)

    out = assemble(text, results)
    out.protected = protected
    rejected: dict[str, int] = {}
    for r in results:
        for c in r.candidates:
            if c.rejected:
                rejected[c.rejected] = rejected.get(c.rejected, 0) + 1
    rewritable = sum(1 for r in results if r.candidates or r.chosen is not r.original)
    out.sentences = results
    out.stats = {
        "sentences": len(results),
        "sentences_considered": rewritable,
        "sentences_changed": sum(1 for r in results if r.chosen is not r.original),
        "candidates": n_candidates,
        "rejected": rejected,
        "languagetool": lt_on,
        "seconds": round(time.perf_counter() - t0, 3),
    }
    return out


VOICE_WEIGHT = 0.35  # share of style_fit given to document-level voice movement
VOICE_SCALE = 40.0  # a gain of 0.0125 in voice distance maps to the full component


def apply_voice(
    voice: VoiceObjective, index: int, original: Candidate, cands: list[Candidate]
) -> None:
    """Blend each candidate's effect on the document's Voice Match into its style fit."""
    original.style = (1 - VOICE_WEIGHT) * original.style + VOICE_WEIGHT * 0.5
    original.score = total(original)
    for c in cands:
        gain = voice.gain(index, c.text)
        comp = max(0.0, min(1.0, 0.5 + VOICE_SCALE * gain))
        c.style = (1 - VOICE_WEIGHT) * c.style + VOICE_WEIGHT * comp
        c.score = total(c)


REVERT_MARGIN = 0.015  # only undo rewrites whose quality gain was small


def voice_revert_pass(
    results: list[SentenceResult], profile: dict[str, Any] | None, intensity: int
) -> None:
    """Final U1 check on the whole document: undo low-value rewrites that pull it away from
    the student's voice (greedy, largest voice gain first)."""
    if not profile:
        return
    live = [r for r in results if r.sentence.text]
    obj = VoiceObjective(profile, [r.chosen.text for r in live])
    order = sorted(range(len(live)), key=lambda i: -obj.gain(i, live[i].original.text))
    for i in order:
        r = live[i]
        if r.chosen is r.original or r.chosen.score - r.original.score > REVERT_MARGIN:
            continue
        if obj.gain(i, r.original.text) > 0.002:
            r.chosen = r.original
            obj.commit(i, r.original.text)


def grammar_pass(results: list[SentenceResult], intensity: int, prefer: str = "score") -> None:
    """Grammar gate in two batched LanguageTool rounds.

    Round 1 checks only each sentence's current choice; matches away from its edits already
    existed in the original, so a clean result near the edits is accepted directly. Round 2
    checks the originals and runners-up of the sentences that failed round 1.
    """
    firsts = [(ri, r.chosen) for ri, r in enumerate(results) if r.chosen is not r.original]
    matches = grammar.check_raw([c.text for _, c in firsts])
    retry: list[int] = []
    for (ri, c), ms in zip(firsts, matches, strict=True):
        near = grammar.near(ms, edit_spans(c)[1])
        if near:
            retry.append(ri)
        else:
            apply_grammar(0, c, 0)
    if not retry:
        return
    texts: list[str] = []
    owners: list[tuple[int, Candidate | None]] = []  # None = the original sentence
    for ri in retry:
        r = results[ri]
        texts.append(r.original.text)
        owners.append((ri, None))
        alive = sorted((c for c in r.candidates if c.rejected is None), key=lambda c: -c.score)
        for cand in alive[:GRAMMAR_CHECK_TOP]:
            texts.append(cand.text)
            owners.append((ri, cand))
        for cand in alive[GRAMMAR_CHECK_TOP:]:
            cand.rejected = "unchecked"
    found = grammar.check_raw(texts)
    originals = {ri: ms for (ri, o), ms in zip(owners, found, strict=True) if o is None}
    for (ri, owner), ms in zip(owners, found, strict=True):
        if owner is None:
            continue
        old_spans, new_spans = edit_spans(owner)
        before = grammar.near(originals[ri], old_spans)
        after = grammar.near(ms, new_spans)
        apply_grammar(0, owner, grammar.new_errors(before, after))
    for ri in retry:
        r = results[ri]
        r.chosen = choose(r.original, r.candidates, intensity, prefer)


def _advance(ctx: HumanizeContext, sent: Sentence, view: SentenceView, chosen: Candidate) -> None:
    """Update rolling context (openers, recent lemmas, swapped lemmas) after a sentence."""
    ctx.chosen.append(chosen.text)
    op = opening_transition(chosen.text)
    ctx.chosen_openers.append(op[0] if op else "")
    ctx.recent_lemmas.append(set(content_lemmas(sent.span.as_doc())))
    if len(ctx.recent_lemmas) > 3:
        ctx.recent_lemmas.pop(0)
    if chosen.edits:
        synonym.record_swaps(ctx, sent.paragraph, chosen, view)


def assemble(text: str, results: list[SentenceResult]) -> HumanizeOutput:
    parts: list[str] = []
    changes: list[ChangeRecord] = []
    pos = 0
    delta = 0
    for r in sorted(results, key=lambda r: r.sentence.start):
        s = r.sentence
        parts.append(text[pos : s.start])
        chosen = r.chosen
        parts.append(chosen.text)
        conf = confidence(chosen) if chosen.edits else 1.0
        local_delta = 0
        for e in chosen.edits:
            o_s, o_e = s.start + e.start, s.start + e.end
            n_s = o_s + delta + local_delta
            n_e = n_s + len(e.replacement)
            changes.append(
                ChangeRecord(
                    id=hashlib.sha1(f"{o_s}:{o_e}:{e.replacement}".encode()).hexdigest()[:10],
                    orig_start=o_s,
                    orig_end=o_e,
                    new_start=n_s,
                    new_end=n_e,
                    original=text[o_s:o_e],
                    replacement=e.replacement,
                    transform=e.transform,
                    category=e.category or CATEGORY_BY_TRANSFORM[e.transform],
                    reason=e.reason,
                    confidence=conf,
                )
            )
            local_delta += len(e.replacement) - (e.end - e.start)
        delta += len(chosen.text) - len(s.text)
        pos = s.end
    parts.append(text[pos:])
    return HumanizeOutput(text="".join(parts), changes=changes, protected=[])
