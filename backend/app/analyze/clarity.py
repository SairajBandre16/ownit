"""Clarity: readability grade, long sentences, nominalizations, wordy phrases."""

from __future__ import annotations

from functools import lru_cache

import textstat

from app.analyze.base import AnalyzerContext, MetricResult, make_issue
from app.core.explain import explain
from app.core.lexicon import PhraseLexicon, inflect, lexicon
from app.core.nlp import zipf

LONG_SENTENCE = 30
NOMINAL_SUFFIXES = ("tion", "sion", "ment", "ance", "ence")
LIGHT_VERBS = {
    "make",
    "give",
    "take",
    "have",
    "perform",
    "conduct",
    "carry",
    "do",
    "provide",
    "reach",
    "achieve",
    "undertake",
}


@lru_cache(maxsize=4096)
def verb_for_noun(noun: str) -> str | None:
    """Most common verb derivationally related to a noun (WordNet), e.g. decision -> decide."""
    from nltk.corpus import wordnet as wn

    candidates: set[str] = set()
    for lemma in wn.lemmas(noun, pos=wn.NOUN):
        for rel in lemma.derivationally_related_forms():
            if rel.synset().pos() == "v" and "_" not in rel.name():
                candidates.add(rel.name().lower())
    # prefer verbs sharing a stem with the noun ("analysis" -> "analyze", not "study")
    stem = noun[: max(3, len(noun) - 5)]
    ranked = sorted(candidates, key=lambda v: (not v.startswith(stem[:3]), -zipf(v)))
    return ranked[0] if ranked else None


def is_nominalization(word: str) -> bool:
    w = word.lower()
    return len(w) > 6 and w.endswith(NOMINAL_SUFFIXES)


def wordy_lexicon() -> PhraseLexicon:
    return lexicon("wordy_phrases")


def analyze(ctx: AnalyzerContext) -> MetricResult:
    seg = ctx.seg
    sents = seg.body_sentences
    issues = []

    # --- readability grade (body text only)
    body_text = " ".join(s.text for s in sents)
    grade = float(textstat.flesch_kincaid_grade(body_text)) if body_text.strip() else 0.0
    grade_excess = max(0.0, grade - ctx.target_grade)

    # --- long sentences
    long_count = 0
    for s in sents:
        if s.words > LONG_SENTENCE:
            long_count += 1
            issues.append(
                make_issue(
                    start=s.start,
                    end=s.end,
                    category="clarity",
                    rule="long_sentence",
                    severity="warn" if s.words > 40 else "info",
                    message=explain("issue.long_sentence", n=s.words),
                    lesson_slug="sentence-length",
                )
            )

    # --- nominalizations (density) + light-verb constructions (issues)
    nominal_count = 0
    for s in sents:
        for tok in s.span:
            if tok.pos_ != "NOUN" or not is_nominalization(tok.text):
                continue
            if ctx.all_index.overlaps(tok.idx, tok.idx + len(tok)) and tok.ent_type_:
                continue
            nominal_count += 1
            head = tok.head
            if tok.dep_ == "dobj" and head.pos_ == "VERB" and head.lemma_ in LIGHT_VERBS:
                start, end = head.idx, tok.idx + len(tok)
                verb = verb_for_noun(tok.lemma_.lower())
                phrase = seg.text[start:end]
                if verb:
                    suggestion = inflect(verb, head.tag_)
                    msg = explain("issue.nominalization", phrase=phrase, verb=suggestion)
                else:
                    suggestion = None
                    msg = explain("issue.nominalization_plain", phrase=phrase)
                issues.append(
                    make_issue(
                        start=start,
                        end=end,
                        category="clarity",
                        rule="nominalization",
                        severity="info",
                        message=msg,
                        suggestion=suggestion,
                        lesson_slug="nominalizations",
                    )
                )

    # --- wordy phrases
    wordy = 0
    for m in wordy_lexicon().find(seg.text, seg.doc):
        if ctx.hard_index.overlaps(m.start, m.end) or not ctx.in_body(m.start):
            continue
        wordy += 1
        repl = PhraseLexicon.render(m.value, m) if m.value else ""
        msg = (
            explain("issue.wordy_phrase", phrase=m.text, replacement=repl)
            if repl
            else explain("issue.wordy_phrase_delete", phrase=m.text)
        )
        issues.append(
            make_issue(
                start=m.start,
                end=m.end,
                category="clarity",
                rule="wordy_phrase",
                severity="warn",
                message=msg,
                suggestion=repl,
                lesson_slug="concision",
            )
        )

    n_sents = max(len(sents), 1)
    return MetricResult(
        name="clarity",
        metrics={
            "fk_grade": round(grade, 2),
            "grade_excess": grade_excess,
            "long_sentence_pct": 100.0 * long_count / n_sents,
            "nominalizations_per_100w": ctx.per_100w(nominal_count),
            "wordy_per_100w": ctx.per_100w(wordy),
        },
        issues=issues,
    )
