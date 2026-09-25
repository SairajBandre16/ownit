"""Document pass (CLAUDE.md §6.3): after each sentence has its best candidate, look at the
whole document.

1. merge_short (§6.2.5): two consecutive short sentences (< 9 words each) that share a subject,
   or where the second starts with a pronoun referring back, are joined (", and" / "; " / ", so").
2. Rhythm + openers: if sentence-length variety is below target, or 3+ sentences in a row open
   the same way, swap in a runner-up candidate (already scored and gated) that helps.

Every proposal still has to pass the grammar gate (one batched LanguageTool round).
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from app.core.explain import explain
from app.core.nlp import parse
from app.humanize.ranking import grammar
from app.humanize.ranking.scorer import MIN_IMPROVEMENT, apply_grammar, edit_spans, score_candidates
from app.humanize.ranking.style_fit import StyleTargets
from app.humanize.text_utils import lower_first
from app.humanize.transforms.opener_vary import cheap_key
from app.humanize.types import Candidate, HumanizeContext, LocalEdit

SHORT = 9
TARGET_SD = {"academic": 6.0, "neutral": 6.5, "casual": 7.0}
SWAP_TOLERANCE = 0.03  # a runner-up may score this much below the chosen candidate
BACK_REFERENCE = {"it", "they", "this", "these", "he", "she", "we"}


@dataclass
class MergedSentence:
    """Stand-in for a Sentence covering two merged sentences (assemble() needs these fields)."""

    start: int
    end: int
    text: str
    paragraph: int
    section: str

    @property
    def words(self) -> int:
        return len(self.text.split())


def _words(text: str) -> int:
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


def _subject_lemma(text: str) -> str | None:
    doc = parse(text)
    for t in doc:
        if t.dep_ in ("nsubj", "nsubjpass") and t.head.dep_ == "ROOT":
            return t.lemma_.lower()
    return None


def _merge_text(a: str, b: str) -> tuple[str, str] | None:
    """(joined text, joiner) for two short sentences, or None if they shouldn't be joined."""
    if not a.endswith(".") or a.endswith("..") or not b[:1].isupper():
        return None
    first = b.split(" ", 1)[0].strip(",").lower()
    body_b = b
    if first in ("however",):
        m = re.match(r"^However,\s*", b)
        if not m:
            return None
        return a[:-1] + "; however, " + lower_first(b[m.end() :]), "; however,"
    if first in ("so", "therefore", "thus"):
        m = re.match(r"^(So|Therefore|Thus),?\s*", b)
        if not m:
            return None
        return a[:-1] + ", so " + lower_first(b[m.end() :]), ", so"
    if first in BACK_REFERENCE:
        return a[:-1] + ", and " + lower_first(body_b), ", and"
    sa, sb = _subject_lemma(a), _subject_lemma(b)
    if sa and sb and sa == sb:
        return a[:-1] + ", and " + lower_first(body_b), ", and"
    return None


def merge_pass(results, ctx: HumanizeContext, targets: StyleTargets) -> list[tuple[int, Candidate]]:  # type: ignore[no-untyped-def]
    """Propose merged candidates for pairs (index of the first result, candidate)."""
    proposals: list[tuple[int, Candidate]] = []
    i = 0
    while i < len(results) - 1:
        r1, r2 = results[i], results[i + 1]
        s1, s2 = r1.sentence, r2.sentence
        rewritable = r1.rewritable and r2.rewritable
        c1, c2 = r1.chosen, r2.chosen
        if (
            not rewritable
            or s1.paragraph != s2.paragraph
            or not (2 <= _words(c1.text) < SHORT and 2 <= _words(c2.text) < SHORT)
        ):
            i += 1
            continue
        joined = _merge_text(c1.text, c2.text)
        if not joined:
            i += 1
            continue
        text_a, joiner = joined
        cand = _merged_candidate(results, i, text_a, joiner)
        if cand is not None:
            proposals.append((i, cand))
            i += 2
        else:
            i += 1
    return proposals


def _merged_candidate(results, i: int, merged_text: str, joiner: str) -> Candidate | None:  # type: ignore[no-untyped-def]
    """Candidate over the combined original span of results i and i+1."""
    r1, r2 = results[i], results[i + 1]
    s1, s2 = r1.sentence, r2.sentence
    gap = s2.start - s1.end
    if gap < 1:
        return None
    original_text = s1.text + (" " * gap) + s2.text
    # edits of each chosen candidate must not touch the boundary region
    for e in r1.chosen.edits:
        if e.end >= len(s1.text) - 1:
            return None
    first_word_len = len(s2.text.split(" ", 1)[0])
    for e in r2.chosen.edits:
        if e.start <= first_word_len:
            return None
    # boundary edit: ". It" -> ", and it" in combined-original coordinates
    b_start = len(s1.text) - 1
    b_end = len(s1.text) + gap + first_word_len
    c1_end, c2_start = r1.chosen.text[:-1], r2.chosen.text
    boundary_new = merged_text[len(c1_end) : len(merged_text) - (len(c2_start) - first_word_len)]
    boundary = LocalEdit(
        start=b_start,
        end=b_end,
        replacement=boundary_new,
        transform="merge_short",
        reason=explain("transform.merge_short", a=_words(r1.chosen.text), b=_words(r2.chosen.text)),
        category="rhythm",
    )
    shift = len(s1.text) + gap
    edits = (
        list(r1.chosen.edits)
        + [boundary]
        + [
            LocalEdit(
                e.start + shift, e.end + shift, e.replacement, e.transform, e.reason, e.category
            )
            for e in r2.chosen.edits
        ]
    )
    # rebuild the text from the original + edits and check it equals the intended merge
    out = original_text
    for e in sorted(edits, key=lambda e: -e.start):
        out = out[: e.start] + e.replacement + out[e.end :]
    if out != merged_text:
        return None
    cand = Candidate(
        edits=tuple(sorted(edits, key=lambda e: e.start)), transforms=("merge_short",), text=out
    )
    cand.__dict__["_original_text"] = original_text
    return cand


def document_pass(results, ctx: HumanizeContext, intensity: int, targets: StyleTargets) -> None:  # type: ignore[no-untyped-def]
    proposals: list[tuple[str, int, Candidate]] = []

    # --- rhythm / opener swaps between already-gated candidates
    lengths = [_words(r.chosen.text) for r in results if r.candidates or r.chosen is not r.original]
    target_sd = targets.length_sd or TARGET_SD.get(ctx.tone, 6.0)
    sd = statistics.pstdev(lengths) if len(lengths) > 1 else target_sd
    keys = [cheap_key(r.chosen.text) for r in results]
    for ri, r in enumerate(results):
        alts = [
            c
            for c in r.candidates
            if c is not r.chosen
            and c.rejected in (None, "unchecked")
            and c.score >= r.original.score + MIN_IMPROVEMENT.get(intensity, 0.0)
            and c.score >= r.chosen.score - SWAP_TOLERANCE
        ]
        if not alts:
            continue
        run = ri >= 2 and keys[ri] == keys[ri - 1] == keys[ri - 2]
        best = None
        for c in sorted(alts, key=lambda c: -c.score):
            new_key = cheap_key(c.text)
            if run and new_key != keys[ri]:
                best = c
                break
            if sd < target_sd and len(c.text.split(". ")) > len(r.chosen.text.split(". ")):
                best = c  # a split adds rhythm variety
                break
        if best is not None:
            proposals.append(("swap", ri, best))

    # --- merges of short sentence pairs (intensity 4+)
    if intensity >= 4:
        for i, cand in merge_pass(results, ctx, targets):
            proposals.append(("merge", i, cand))

    if not proposals:
        return

    # score merges (fluency/meaning/style against the two original sentences)
    for kind, _i, cand in proposals:
        if kind != "merge":
            continue
        original = Candidate(edits=(), transforms=(), text=cand.__dict__["_original_text"])
        doc = parse(original.text)
        score_candidates(original, [cand], doc, targets)

    # grammar gate for everything proposed (one batch)
    checkable = [(k, i, c) for k, i, c in proposals if c.rejected in (None, "unchecked")]
    found = (
        grammar.check_raw([c.text for _, _, c in checkable])
        if grammar.available()
        else [[] for _ in checkable]
    )
    merged_away: set[int] = set()
    for (kind, i, cand), ms in zip(checkable, found, strict=True):
        near = grammar.near(ms, edit_spans(cand)[1])
        apply_grammar(0, cand, sum(near.values()))
        if cand.rejected not in (None, "unchecked"):
            continue
        cand.rejected = None
        if kind == "swap" and i not in merged_away:
            results[i].chosen = cand
        elif kind == "merge" and i not in merged_away and i + 1 not in merged_away:
            r1, r2 = results[i], results[i + 1]
            s1, s2 = r1.sentence, r2.sentence
            merged = MergedSentence(
                start=s1.start,
                end=s2.end,
                text=cand.__dict__["_original_text"],
                paragraph=s1.paragraph,
                section=getattr(s1, "section", "body"),
            )
            r1.sentence = merged  # type: ignore[assignment]
            r1.chosen = cand
            r1.original = Candidate(edits=(), transforms=(), text=merged.text)
            # the second sentence is now part of the first: leave an empty placeholder
            r2.sentence = MergedSentence(s2.end, s2.end, "", s2.paragraph, "")  # type: ignore[assignment]
            r2.original = r2.chosen = Candidate(edits=(), transforms=(), text="")
            merged_away.update({i, i + 1})
