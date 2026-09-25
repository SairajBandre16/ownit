"""'Make it yours' (CLAUDE.md §9.3): find generic spots where the student should add their own
examples, data or opinions.

Rules (lexicons in resources/generic_patterns.json):

- abstract_claim     "plays a crucial role in", "is widely used in" … with no example
                     (for example / such as / a name / a number) in the sentence or the next
- vague_source       "studies show", "it is well known" … with no citation in the sentence
- vague_benefit      "improves efficiency", "reduces costs" … with no figure nearby
- results_no_number  a Results/Discussion sentence that reports an outcome ("increased",
                     "higher", "the efficiency …") but has no number, unit or figure reference
- vague_quantifier   "various", "a wide range of" … with no number in the sentence
- vague_intensifier  "significantly", "drastically" … with no figure in the sentence or the next
- vague_time         "in recent years", "nowadays" … with no year or date nearby
- conclusion_no_voice  a Conclusion with no first-person or evaluative sentence
- no_concrete_run    3+ consecutive sentences with no proper noun, number or unit

At most one spot per sentence (the most specific rule wins) and two per paragraph. Each spot
says where the student's answer goes (`insert_at`: the end of the sentence it belongs to).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache, lru_cache
from typing import Any

from app.core.lexicon import LexMatch, PhraseLexicon
from app.core.protect import Protected, detect_protected
from app.core.resources import load
from app.core.segment import Segmentation, Sentence, segment
from app.core.spans import SpanIndex

# most specific first: when two rules fire on one sentence, the earlier one is kept
PRIORITY = [
    "conclusion_no_voice",
    "abstract_claim",
    "vague_source",
    "vague_benefit",
    "results_no_number",
    "vague_quantifier",
    "vague_intensifier",
    "vague_time",
    "no_concrete_run",
]
PHRASE_RULES = {
    "abstract_claim": "abstract_claims",
    "vague_source": "vague_sources",
    "vague_benefit": "vague_benefits",
    "vague_quantifier": "vague_quantifiers",
    "vague_intensifier": "vague_intensifiers",
    "vague_time": "vague_times",
}
# rules whose phrase is only generic when no evidence is in the same sentence (False) or in
# the same or the next sentence (True)
LOOK_AHEAD = {
    "abstract_claim": True,
    "vague_source": False,
    "vague_benefit": True,
    "vague_quantifier": False,
    "vague_intensifier": True,
    "vague_time": True,
}
SKIP_KINDS = {"quote", "code", "equation", "url"}
NUMBER_KINDS = {"number", "reference"}
RESULT_SECTIONS = {"results", "discussion"}
SKIP_SECTIONS = {"references", "acknowledgements", "appendix"}
CONCRETE_ENTS = {
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "PRODUCT",
    "FAC",
    "EVENT",
    "LAW",
    "WORK_OF_ART",
    "QUANTITY",
    "PERCENT",
    "MONEY",
    "CARDINAL",
}
YEAR_RE = re.compile(r"\b(?:1[89]|20)\d{2}s?\b")
ABBREV_DOTS_RE = re.compile(r"(?i)\b(?:i\.e|e\.g)\.?")
DIGIT_RE = re.compile(r"\d")
RUN_LENGTH = 3
MAX_PER_PARAGRAPH = 2
MAX_SPOTS = 25
MIN_WORDS = 5


@dataclass(frozen=True)
class Spot:
    id: str
    start: int  # the generic phrase (or sentence) to highlight
    end: int
    insert_at: int  # where the student's answer is inserted (end of the sentence)
    pattern: str
    label: str
    prompt: str
    starter: str
    quote: str


@lru_cache(maxsize=1)
def patterns() -> dict[str, Any]:
    return load("generic_patterns")  # type: ignore[no-any-return]


@cache
def _lexicon(group: str) -> PhraseLexicon:
    return PhraseLexicon({p.lower(): group for p in patterns()[group]})


@cache
def _word_set(group: str) -> frozenset[str]:
    return frozenset(w.lower() for w in patterns()[group])


@cache
def _phrase_regex(group: str) -> re.Pattern[str]:
    words = sorted(patterns()[group], key=len, reverse=True)
    alts = "|".join(re.escape(w) for w in words)
    return re.compile(rf"(?<![\w-])(?:{alts})(?![\w-])", re.IGNORECASE)


# ---------------------------------------------------------------- sentence evidence
class Evidence:
    """What a sentence already contains that makes it specific."""

    def __init__(self, seg: Segmentation, protected: list[Protected]) -> None:
        self.seg = seg
        self.numbers = SpanIndex((p.start, p.end) for p in protected if p.kind in NUMBER_KINDS)
        self.citations = SpanIndex((p.start, p.end) for p in protected if p.kind == "citation")
        self.skip = SpanIndex((p.start, p.end) for p in protected if p.kind in SKIP_KINDS)
        self.abbrs = SpanIndex((p.start, p.end) for p in protected if p.kind == "abbreviation")

    def has_number(self, s: Sentence) -> bool:
        return (
            self.numbers.overlaps(s.start, s.end)
            or bool(DIGIT_RE.search(s.text))
            # number words count when they count something ("three samples"), not "the old one"
            or any(t.like_num and t.dep_ == "nummod" for t in s.span)
        )

    def has_citation(self, s: Sentence) -> bool:
        return self.citations.overlaps(s.start, s.end)

    @staticmethod
    def _entities(s: Sentence) -> bool:
        # a capitalised first word ("Blockchain technology …") is often mis-tagged as a name
        return any(e.label_ in CONCRETE_ENTS and e.start != s.span.start for e in s.span.ents)

    def has_example(self, s: Sentence) -> bool:
        return bool(
            _phrase_regex("example_markers").search(s.text)
            or self.has_number(s)
            or self.has_citation(s)
            or self._entities(s)
        )

    def has_date(self, s: Sentence) -> bool:
        # "in recent years" is a DATE entity too; only dates with a figure are specific
        return bool(YEAR_RE.search(s.text)) or any(
            e.label_ == "DATE" and DIGIT_RE.search(e.text) for e in s.span.ents
        )

    def is_concrete(self, s: Sentence) -> bool:
        if self.has_number(s) or self.has_citation(s) or self.abbrs.overlaps(s.start, s.end):
            return True
        # proper nouns, except a capitalised first word the tagger calls PROPN
        return any(t.pos_ == "PROPN" and t.i != s.span.start for t in s.span) or self._entities(s)

    def has_voice(self, s: Sentence) -> bool:
        text = ABBREV_DOTS_RE.sub(" ", s.text)  # "i.e." is not the pronoun "I"
        return bool(_phrase_regex("voice_markers").search(text))


# ---------------------------------------------------------------- helpers
def _subject(s: Sentence, offset: int) -> str:
    """Short noun phrase for the subject of the verb at `offset` ("IoT sensors"), or "this"."""
    span = s.span.doc.char_span(offset, offset + 1, alignment_mode="expand")
    tok = span[0] if span is not None and len(span) else s.span.root
    subj = None
    lo, hi = s.span.start, s.span.end  # the whole-document parse can cross line breaks
    for _ in range(4):  # climb from the matched word to the verb that has a subject
        subj = next(
            (c for c in tok.children if c.dep_ in ("nsubj", "nsubjpass") and lo <= c.i < hi),
            None,
        )
        if subj is not None or tok.head is tok:
            break
        tok = tok.head
    if subj is None or subj.pos_ == "PRON":
        return "this"
    toks = [
        t
        for t in subj.subtree
        if t.dep_ not in ("relcl", "punct", "appos", "acl") and not t.is_space and lo <= t.i < hi
    ]
    words = [t.text for t in toks if not (t.i == toks[0].i and t.pos_ == "DET")]
    if not words or len(words) > 6:
        return "this"
    phrase = " ".join(words)
    return phrase if phrase[:2].isupper() else phrase[0].lower() + phrase[1:]


def _render(pattern: str, phrase: str = "", subject: str = "this") -> tuple[str, str, str]:
    p = patterns()["prompts"][pattern]
    prompt = p["prompt"].replace("{phrase}", phrase).replace("{subject}", subject)
    return p["label"], prompt, p["starter"]


def _spot(pattern: str, start: int, end: int, insert_at: int, text: str, **fmt: str) -> Spot:
    label, prompt, starter = _render(pattern, **fmt)
    return Spot(
        id=f"sp-{pattern}-{start}",
        start=start,
        end=end,
        insert_at=insert_at,
        pattern=pattern,
        label=label,
        prompt=prompt,
        starter=starter,
        quote=text[start:end],
    )


def _sentence_end(s: Sentence) -> int:
    """Insertion point: right after the sentence's final punctuation."""
    return s.start + len(s.text.rstrip())


# ---------------------------------------------------------------- rules
def _phrase_spots(seg: Segmentation, sents: list[Sentence], ev: Evidence) -> dict[int, list[Spot]]:
    """Lexicon rules, keyed by sentence position in `sents`."""
    out: dict[int, list[Spot]] = {}
    for i, s in enumerate(sents):
        nxt = sents[i + 1] if i + 1 < len(sents) and sents[i + 1].paragraph == s.paragraph else None
        for pattern, group in PHRASE_RULES.items():
            matches: list[LexMatch] = _lexicon(group).find(s.text)
            for m in matches:
                start, end = s.start + m.start, s.start + m.end
                if ev.skip.overlaps(start, end):
                    continue
                if _has_evidence(pattern, s, nxt, ev):
                    continue
                subject = _subject(s, start) if pattern == "abstract_claim" else "this"
                out.setdefault(i, []).append(
                    _spot(
                        pattern,
                        start,
                        end,
                        _sentence_end(s),
                        seg.text,
                        phrase=m.text,
                        subject=subject,
                    )
                )
                break  # one match per rule per sentence
    return out


def _has_evidence(pattern: str, s: Sentence, nxt: Sentence | None, ev: Evidence) -> bool:
    around = [s, nxt] if LOOK_AHEAD[pattern] and nxt is not None else [s]
    if pattern == "abstract_claim":
        return any(ev.has_example(x) for x in around)
    if pattern == "vague_source":
        return ev.has_citation(s) or bool(re.search(r"\[\d", s.text))
    if pattern == "vague_time":
        return any(ev.has_date(x) for x in around)
    return any(ev.has_number(x) for x in around)


def _results_spots(sents: list[Sentence], ev: Evidence, text: str) -> dict[int, list[Spot]]:
    cues = _word_set("quantitative_cues")
    out: dict[int, list[Spot]] = {}
    for i, s in enumerate(sents):
        if s.section not in RESULT_SECTIONS or ev.has_number(s) or s.text.rstrip().endswith("?"):
            continue
        reports = any(
            t.lemma_.lower() in cues or t.tag_ in ("JJR", "RBR", "JJS", "RBS") for t in s.span
        )
        if reports:
            out.setdefault(i, []).append(
                _spot("results_no_number", s.start, _sentence_end(s), _sentence_end(s), text)
            )
    return out


def _conclusion_spot(sents: list[Sentence], ev: Evidence, text: str) -> tuple[int, Spot] | None:
    idx = [i for i, s in enumerate(sents) if s.section == "conclusion"]
    if not idx or any(ev.has_voice(sents[i]) for i in idx):
        return None
    last = sents[idx[-1]]
    return idx[-1], _spot(
        "conclusion_no_voice", last.start, _sentence_end(last), _sentence_end(last), text
    )


def _run_spots(sents: list[Sentence], ev: Evidence, text: str) -> dict[int, list[Spot]]:
    out: dict[int, list[Spot]] = {}
    run: list[int] = []

    def close() -> None:
        if len(run) >= RUN_LENGTH:
            last = sents[run[-1]]  # highlight the last sentence of the run; add after it
            spot = _spot(
                "no_concrete_run", last.start, _sentence_end(last), _sentence_end(last), text
            )
            out.setdefault(run[-1], []).append(spot)
        run.clear()

    for i, s in enumerate(sents):
        if run and sents[run[-1]].section != s.section:
            close()
        if ev.is_concrete(s):
            close()
        else:
            run.append(i)
    close()
    return out


# ---------------------------------------------------------------- entry point
def find_spots(text: str, seg: Segmentation | None = None) -> list[Spot]:
    seg = seg or segment(text)
    heading_paras = {p.index for p in seg.paragraphs if p.is_heading}
    sents = [
        s
        for s in seg.sentences
        if s.paragraph not in heading_paras
        and s.section not in SKIP_SECTIONS
        and s.words >= MIN_WORDS
    ]
    if not sents:
        return []
    ev = Evidence(seg, detect_protected(text))

    by_sentence: dict[int, list[Spot]] = {}
    for rule_out in (
        _phrase_spots(seg, sents, ev),
        _results_spots(sents, ev, text),
        _run_spots(sents, ev, text),
    ):
        for i, spots in rule_out.items():
            by_sentence.setdefault(i, []).extend(spots)
    concl = _conclusion_spot(sents, ev, text)
    if concl:
        by_sentence.setdefault(concl[0], []).append(concl[1])

    rank = {p: n for n, p in enumerate(PRIORITY)}
    chosen: list[tuple[int, Spot]] = []
    per_paragraph: dict[int, int] = {}
    for i in sorted(by_sentence):
        best = min(by_sentence[i], key=lambda sp: rank[sp.pattern])
        chosen.append((i, best))
    # keep the most specific spots when a paragraph has too many
    chosen.sort(key=lambda x: (rank[x[1].pattern], x[1].start))
    kept: list[Spot] = []
    for i, sp in chosen:
        para = sents[i].paragraph
        if per_paragraph.get(para, 0) >= MAX_PER_PARAGRAPH:
            continue
        per_paragraph[para] = per_paragraph.get(para, 0) + 1
        kept.append(sp)
    kept = kept[:MAX_SPOTS]
    return sorted(kept, key=lambda sp: sp.start)
