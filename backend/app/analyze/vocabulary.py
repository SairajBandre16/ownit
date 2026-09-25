"""Vocabulary: lexical diversity (MTLD), nearby repetition, stock phrases, clichés."""

from __future__ import annotations

from app.analyze.base import AnalyzerContext, MetricResult, make_issue
from app.core.explain import explain
from app.core.lexicon import PhraseLexicon, lexicon

MTLD_THRESHOLD = 0.72
CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV"}
# very common lemmas whose repetition is natural and not worth flagging
REPEAT_EXEMPT = {
    "be",
    "have",
    "do",
    "make",
    "get",
    "go",
    "say",
    "take",
    "give",
    "use",
    "include",
    "also",
    "however",
    "more",
    "most",
    "such",
    "other",
    "one",
    "first",
    "new",
    "well",
    "only",
    "very",
    "system",
    "result",
    "value",
    "data",
    "time",
    "figure",
    "table",
    "show",
    "can",
    "not",
}


def _mtld_pass(tokens: list[str]) -> float:
    factors = 0.0
    types: set[str] = set()
    count = 0
    for tok in tokens:
        count += 1
        types.add(tok)
        ttr = len(types) / count
        if ttr <= MTLD_THRESHOLD:
            factors += 1
            types.clear()
            count = 0
    if count > 0:
        ttr = len(types) / count
        factors += (1 - ttr) / (1 - MTLD_THRESHOLD) if ttr < 1 else 0.0
    return len(tokens) / factors if factors > 0 else float(len(tokens))


def mtld(tokens: list[str]) -> float:
    """Measure of Textual Lexical Diversity (McCarthy & Jarvis 2010), bidirectional mean."""
    if len(tokens) < 10:
        return 0.0
    return (_mtld_pass(tokens) + _mtld_pass(tokens[::-1])) / 2


def ai_lexicon() -> PhraseLexicon:
    return lexicon("ai_style_phrases")


def cliche_lexicon() -> PhraseLexicon:
    return lexicon("cliches")


def analyze(ctx: AnalyzerContext) -> MetricResult:
    seg = ctx.seg
    sents = seg.body_sentences
    issues = []

    words = [t.lower_ for s in sents for t in s.span if t.is_alpha]
    diversity = mtld(words)

    # --- repeated content lemmas within 2 sentences
    repeats = 0
    for i, s in enumerate(sents):
        window = sents[max(0, i - 2) : i]
        seen = {
            t.lemma_.lower()
            for w in window
            if w.paragraph == s.paragraph
            for t in w.span
            if t.pos_ in CONTENT_POS
        }
        flagged: set[str] = set()
        for t in s.span:
            lemma = t.lemma_.lower()
            if (
                t.pos_ not in CONTENT_POS
                or t.is_stop
                or len(lemma) < 4
                or lemma in REPEAT_EXEMPT
                or lemma in flagged
                or lemma not in seen
                or ctx.all_index.overlaps(t.idx, t.idx + len(t))
            ):
                continue
            flagged.add(lemma)
            repeats += 1
            issues.append(
                make_issue(
                    start=t.idx,
                    end=t.idx + len(t),
                    category="vocabulary",
                    rule="repeated_word",
                    severity="info",
                    message=explain("issue.repeated_word", word=t.text),
                    lesson_slug="word-choice",
                )
            )

    # --- stock / AI-style phrases
    stock = 0
    for m in ai_lexicon().find(seg.text, seg.doc):
        if ctx.hard_index.overlaps(m.start, m.end) or not ctx.in_body(m.start):
            continue
        stock += 1
        entry = m.value
        repl = entry.get("replacement")
        suggestion = PhraseLexicon.render(repl, m) if repl is not None else None
        issues.append(
            make_issue(
                start=m.start,
                end=m.end,
                category="vocabulary",
                rule="ai_style_phrase",
                severity="warn",
                message=explain("issue.ai_style_phrase", phrase=m.text, note=entry["note"]),
                suggestion=suggestion,
                lesson_slug="stock-phrases",
            )
        )

    # --- clichés
    cliches = 0
    for m in cliche_lexicon().find(seg.text, seg.doc):
        if ctx.hard_index.overlaps(m.start, m.end) or not ctx.in_body(m.start):
            continue
        cliches += 1
        hint = f"Try '{m.value}'." if m.value else "Say it in your own words."
        issues.append(
            make_issue(
                start=m.start,
                end=m.end,
                category="vocabulary",
                rule="cliche",
                severity="info",
                message=explain("issue.cliche", phrase=m.text, hint=hint),
                suggestion=m.value,
                lesson_slug="cliches",
            )
        )

    return MetricResult(
        name="vocabulary",
        metrics={
            "mtld": diversity,
            "repeats_per_100w": ctx.per_100w(repeats),
            "stock_per_100w": ctx.per_100w(stock),
            "cliche_per_100w": ctx.per_100w(cliches),
        },
        issues=issues,
    )
