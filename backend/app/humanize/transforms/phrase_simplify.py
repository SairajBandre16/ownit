"""phrase_simplify: longest-match replacement of wordy phrases, stock phrases, fillers and
weak verb + noun constructions (CLAUDE.md §6.2.1)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from lemminflect import getLemma

from app.core.lexicon import LexMatch, PhraseLexicon, lexicon
from app.core.resources import load
from app.humanize.edits import local_rewrite
from app.humanize.text_utils import article_for
from app.humanize.types import Candidate, HumanizeContext, LocalEdit, SentenceView, make_candidate

TRANSFORM = "phrase_simplify"
MAX_SINGLES = 3


@dataclass(frozen=True)
class PhraseHit:
    start: int  # document offsets
    end: int
    text: str
    replacement: str
    kind: str  # stock | weak_verb | wordy | filler
    note: str = ""


@lru_cache(maxsize=1)
def _hedge_free_fillers() -> PhraseLexicon:
    return lexicon("fillers")


def _entries(kind: str, m: LexMatch) -> str | None:
    """Replacement template for a lexicon match, or None if it's flag-only."""
    if kind == "stock":
        return m.value.get("replacement")  # type: ignore[no-any-return]
    if kind == "filler":
        return m.value  # type: ignore[no-any-return]  # "" delete, str replace, None flag-only
    return m.value  # type: ignore[no-any-return]


# order = priority when matches overlap
LEXICONS = (
    ("stock", "ai_style_phrases"),
    ("weak_verb", "weak_verbs"),
    ("wordy", "wordy_phrases"),
    ("filler", "fillers"),
)
# tone-dependent: casual text may keep mild intensifiers
KEEP_IN_CASUAL = {"really", "pretty", "quite", "just", "a lot", "lots of"}


def document_hits(ctx: HumanizeContext) -> list[PhraseHit]:
    cached = getattr(ctx, "_phrase_hits", None)
    if cached is not None:
        return cached  # type: ignore[no-any-return]
    seg = ctx.seg
    hits: list[PhraseHit] = []
    taken: list[tuple[int, int]] = []
    for kind, name in LEXICONS:
        for m in lexicon(name).find(seg.text, seg.doc):
            template = _entries(kind, m)
            if template is None:
                continue
            if ctx.tone == "casual" and kind == "filler" and m.key in KEEP_IN_CASUAL:
                continue
            if any(m.start < e and s < m.end for s, e in taken):
                continue
            repl = PhraseLexicon.render(template, m)
            if repl == m.text:
                continue
            taken.append((m.start, m.end))
            note = m.value.get("note", "") if isinstance(m.value, dict) else ""
            hits.append(PhraseHit(m.start, m.end, m.text, repl, kind, note))
    hits.sort(key=lambda h: h.start)
    ctx._phrase_hits = hits  # type: ignore[attr-defined]
    return hits


def _reason(kind: str, old: str, new: str) -> tuple[str, str]:
    if kind == "stock":
        return (
            ("transform.phrase_simplify.delete", "vocabulary")
            if not new
            else (
                "transform.phrase_simplify.stock",
                "vocabulary",
            )
        )
    if kind == "weak_verb":
        return "transform.phrase_simplify.weak_verb", "voice"
    if kind == "filler":
        return (
            ("transform.phrase_simplify.filler", "voice")
            if not new
            else (
                "transform.phrase_simplify.filler_replace",
                "voice",
            )
        )
    return (
        ("transform.phrase_simplify.delete", "clarity")
        if not new
        else (
            "transform.phrase_simplify.replace",
            "clarity",
        )
    )


def _edit_for(view: SentenceView, hit: PhraseHit) -> LocalEdit | None:
    text = view.text
    s, e = hit.start - view.start, hit.end - view.start
    repl = hit.replacement
    # "for the purpose of measuring" -> "to measure"
    if repl.endswith(" to") or repl == "to":
        tail = text[e:]
        nxt = tail.lstrip()
        word = nxt.split(" ", 1)[0].rstrip(",.;:") if nxt else ""
        if word.endswith("ing") and len(word) > 4:
            base = getLemma(word.lower(), upos="VERB")
            if base:
                gap = len(tail) - len(nxt)
                e = e + gap + len(word)
                repl = f"{repl} {base[0]}"
    # fix a/an before the replaced phrase ("an array of" handled by the phrase itself)
    before = text[:s]
    if repl and before.endswith(("a ", "an ", "A ", "An ")):
        art_start = len(before.rstrip()) - len(before.rstrip().split(" ")[-1])
        article = before[art_start:].strip()
        wanted = article_for(repl.split(" ")[0])
        if article.lower() != wanted:
            wanted = wanted.capitalize() if article[0].isupper() else wanted
            repl = f"{wanted} {repl}"
            s = art_start
    key, category = _reason(hit.kind, hit.text, repl)
    if hit.kind == "stock" and hit.note:
        key = (
            "transform.phrase_simplify.stock_note"
            if repl
            else "transform.phrase_simplify.stock_note_delete"
        )
    return local_rewrite(
        text,
        s,
        e,
        repl,
        TRANSFORM,
        key,
        category=category,
        old=hit.text,
        new=repl.strip(),
        note=hit.note,
    )


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    hits = [h for h in document_hits(ctx) if view.start <= h.start and h.end <= view.sentence.end]
    edits: list[LocalEdit] = []
    for h in hits:
        ed = _edit_for(view, h)
        if ed is not None and not view.touches_protected(ed.start, ed.end):
            edits.append(ed)
    if not edits:
        return []
    out: list[Candidate] = []
    # all edits together, dropping any that collide
    chosen: list[LocalEdit] = []
    for ed in edits:
        if all(not ed.overlaps(c) for c in chosen):
            chosen.append(ed)
    full = make_candidate(view, chosen, (TRANSFORM,))
    if full:
        out.append(full)
    if len(edits) > 1:
        for ed in edits[:MAX_SINGLES]:
            c = make_candidate(view, [ed], (TRANSFORM,))
            if c:
                out.append(c)
    return out


def transition_words() -> set[str]:
    groups = load("transitions")["groups"]
    return {t.lower() for g in groups.values() for t in g}
