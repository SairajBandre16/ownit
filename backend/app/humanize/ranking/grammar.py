"""Grammar penalty: new LanguageTool matches a candidate introduces near its edits.

All texts are checked in as few HTTP requests as possible (joined with blank lines). Only
matches within WINDOW characters of an edit count: errors elsewhere were already in the
original sentence.
"""

from __future__ import annotations

from collections import Counter

from app.core.languagetool import LTMatch
from app.core.nlp import get_languagetool

SEPARATOR = "\n\n"
CHUNK_CHARS = 20000
WINDOW = 20
# style-only rules that shouldn't block a rewrite
IGNORE_RULES = {
    "PASSIVE_VOICE",
    "TOO_LONG_SENTENCE",
    "SENTENCE_WHITESPACE",
    "ENGLISH_WORD_REPEAT_RULE",
    "READABILITY_RULE_SIMPLE",
    "READABILITY_RULE_DIFFICULT",
    "EN_COMPOUNDS",
    "COMMA_COMPOUND_SENTENCE",
    "COMMA_COMPOUND_SENTENCE_2",
}
IGNORE_CATEGORIES = {"STYLE", "REDUNDANCY", "TYPOGRAPHY", "PLAIN_ENGLISH", "WIKIPEDIA", "MISC"}


def available() -> bool:
    return get_languagetool().available()


def check_raw(texts: list[str]) -> list[list[LTMatch]]:
    """LanguageTool matches (offsets relative to each text). Empty lists if offline."""
    lt = get_languagetool()
    results: list[list[LTMatch]] = [[] for _ in texts]
    if not texts or not lt.available():
        return results
    batch: list[int] = []
    size = 0

    def flush() -> None:
        nonlocal batch, size
        if not batch:
            return
        joined = SEPARATOR.join(texts[i] for i in batch)
        bounds = []
        pos = 0
        for i in batch:
            bounds.append((pos, pos + len(texts[i]), i))
            pos += len(texts[i]) + len(SEPARATOR)
        for m in lt.check(joined):
            if m.rule_id in IGNORE_RULES or m.category in IGNORE_CATEGORIES:
                continue
            for s, e, i in bounds:
                if s <= m.start < e:
                    results[i].append(
                        LTMatch(
                            m.start - s,
                            m.end - s,
                            m.rule_id,
                            m.category,
                            m.message,
                            m.replacements,
                            m.issue_type,
                        )
                    )
                    break
        batch, size = [], 0

    for i, t in enumerate(texts):
        if size + len(t) > CHUNK_CHARS:
            flush()
        batch.append(i)
        size += len(t) + len(SEPARATOR)
    flush()
    return results


def near(matches: list[LTMatch], spans: list[tuple[int, int]]) -> Counter[str]:
    """Rule counts of matches within WINDOW chars of any span."""
    out: Counter[str] = Counter()
    for m in matches:
        if any(m.start < e + WINDOW and s - WINDOW < m.end for s, e in spans):
            out[m.rule_id] += 1
    return out


def new_errors(orig: Counter[str], cand: Counter[str]) -> int:
    return sum(max(0, n - orig.get(rule, 0)) for rule, n in cand.items())


def check_many(texts: list[str]) -> list[Counter[str]]:
    """Rule-id counts for each whole text (used by the evaluation harness)."""
    return [Counter(m.rule_id for m in ms) for ms in check_raw(texts)]
