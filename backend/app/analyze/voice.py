"""Voice: passive ratio, hedges, fillers, weak verbs."""

from __future__ import annotations

from functools import lru_cache

from spacy.tokens import Span

from app.analyze.base import AnalyzerContext, MetricResult, make_issue
from app.core.explain import explain
from app.core.lexicon import PhraseLexicon, lexicon
from app.core.resources import load

STACK_WINDOW = 6  # hedges within this many words of each other are "stacked"
_MODALS = {"might", "may", "could", "can", "would", "should"}
_HEDGE_ADVERBS = {"possibly", "perhaps", "potentially", "conceivably", "arguably", "probably"}


def builtin_stack(phrase: str) -> bool:
    """Lexicon entries like "might possibly" already contain two hedges."""
    words = phrase.lower().split()
    return len(words) == 2 and words[0] in _MODALS and words[1] in _HEDGE_ADVERBS


@lru_cache(maxsize=1)
def hedge_lexicon() -> PhraseLexicon:
    return PhraseLexicon({h["phrase"]: h for h in load("hedges")["hedges"]})


def filler_lexicon() -> PhraseLexicon:
    return lexicon("fillers")


def weak_verb_lexicon() -> PhraseLexicon:
    return lexicon("weak_verbs")


def passive_info(span: Span) -> tuple[int, int, str | None] | None:
    """(start, end, agent) of the passive construction in a sentence, or None."""
    for tok in span:
        if tok.dep_ in ("nsubjpass", "auxpass"):
            verb = tok.head
            subj = next((c for c in verb.children if c.dep_ == "nsubjpass"), None)
            candidates = [subj.left_edge if subj is not None else verb]
            candidates += [c for c in verb.children if c.dep_ == "auxpass"]
            start_tok = min(candidates, key=lambda t: t.i)
            agent = None
            end_tok = verb
            for c in verb.children:
                if c.dep_ == "agent":
                    pobj = next((g for g in c.children if g.dep_ == "pobj"), None)
                    if pobj is not None:
                        agent = span.doc[pobj.left_edge.i : pobj.right_edge.i + 1].text
                        end_tok = pobj.right_edge
            return start_tok.idx, end_tok.idx + len(end_tok), agent
    return None


def analyze(ctx: AnalyzerContext) -> MetricResult:
    seg = ctx.seg
    sents = seg.body_sentences
    issues = []

    # --- passive voice (Methodology is exempt: passive is conventional there)
    passive = 0
    counted = 0
    for s in sents:
        if s.section == "methodology":
            continue
        counted += 1
        info = passive_info(s.span)
        if info is None:
            continue
        passive += 1
        start, end, agent = info
        msg = explain("issue.passive_agent", agent=agent) if agent else explain("issue.passive")
        issues.append(
            make_issue(
                start=start,
                end=end,
                category="voice",
                rule="passive",
                severity="info",
                message=msg,
                lesson_slug="passive-voice",
            )
        )

    # --- hedges (stacked hedges are warnings)
    hedge_count = 0
    hedge_matches = [
        m
        for m in hedge_lexicon().find(seg.text, seg.doc)
        if not ctx.hard_index.overlaps(m.start, m.end) and ctx.in_body(m.start)
    ]
    for i, m in enumerate(hedge_matches):
        strength = m.value["strength"]
        prev = hedge_matches[i - 1] if i > 0 else None
        stacked = (
            prev is not None
            and len(seg.text[prev.end : m.start].split()) <= STACK_WINDOW
            and not any(c in seg.text[prev.end : m.start] for c in ".!?")
        )
        if stacked or builtin_stack(m.text):
            first = prev if stacked and prev is not None else m
            a, b = (prev.text, m.text) if stacked and prev is not None else tuple(m.text.split())
            hedge_count += 1
            issues.append(
                make_issue(
                    start=first.start,
                    end=m.end,
                    category="voice",
                    rule="stacked_hedge",
                    severity="warn",
                    message=explain("issue.stacked_hedge", a=a, b=b),
                    lesson_slug="hedging",
                )
            )
        elif strength >= 2:
            hedge_count += 1
            issues.append(
                make_issue(
                    start=m.start,
                    end=m.end,
                    category="voice",
                    rule="hedge",
                    severity="info",
                    message=explain("issue.hedge", phrase=m.text),
                    lesson_slug="hedging",
                )
            )
        elif strength == 1:
            hedge_count += 1

    # --- fillers
    fillers = 0
    for m in filler_lexicon().find(seg.text, seg.doc):
        if ctx.hard_index.overlaps(m.start, m.end) or not ctx.in_body(m.start):
            continue
        if m.value is None:
            continue  # flag-only words that are fine in technical prose don't count
        fillers += 1
        filler_repl = PhraseLexicon.render(m.value, m) if m.value else ""
        hint = f"Try '{filler_repl}'." if filler_repl else "Delete it."
        issues.append(
            make_issue(
                start=m.start,
                end=m.end,
                category="voice",
                rule="filler",
                severity="info",
                message=explain("issue.filler", phrase=m.text, hint=hint),
                suggestion=filler_repl,
                lesson_slug="fillers",
            )
        )

    # --- weak verb + noun constructions, and "There is/are ... that"
    weak = 0
    for m in weak_verb_lexicon().find(seg.text, seg.doc):
        if ctx.hard_index.overlaps(m.start, m.end) or not ctx.in_body(m.start):
            continue
        weak += 1
        repl: str | None = None
        if m.value:
            repl = PhraseLexicon.render(m.value, m)
            msg = explain("issue.weak_verb", phrase=m.text, replacement=repl)
        else:
            msg = explain("issue.weak_verb_plain", phrase=m.text)
        issues.append(
            make_issue(
                start=m.start,
                end=m.end,
                category="voice",
                rule="weak_verb",
                severity="info",
                message=msg,
                suggestion=repl,
                lesson_slug="strong-verbs",
            )
        )
    for s in sents:
        toks = [t for t in s.span if not t.is_space]
        if (
            len(toks) > 3
            and toks[0].lower_ == "there"
            and toks[1].lemma_ == "be"
            and any(t.dep_ == "relcl" or t.lower_ in ("that", "who", "which") for t in toks[2:])
        ):
            weak += 1
            end_tok = toks[1]
            issues.append(
                make_issue(
                    start=toks[0].idx,
                    end=end_tok.idx + len(end_tok),
                    category="voice",
                    rule="expletive",
                    severity="info",
                    message=explain("issue.expletive", be=toks[1].text),
                    lesson_slug="strong-verbs",
                )
            )

    return MetricResult(
        name="voice",
        metrics={
            "passive_ratio": passive / max(counted, 1),
            "hedges_per_100w": ctx.per_100w(hedge_count),
            "fillers_per_100w": ctx.per_100w(fillers),
            "weak_verbs_per_100w": ctx.per_100w(weak),
        },
        issues=issues,
    )
