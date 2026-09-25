"""synonym: WordNet synonyms chosen by Lesk word-sense disambiguation (CLAUDE.md §6.2.2).

Only swaps a word when it helps: the replacement is plainer (more frequent) than a formal /
rare original, or the original repeats a word from a nearby sentence.
Filters: same POS, Zipf ≥ 3.5 and ≥ original − 0.5, vector similarity ≥ 0.45, re-inflected
with lemminflect, ≤ 15 % of eligible words per sentence, each lemma swapped once per paragraph.
"""

from __future__ import annotations

from functools import lru_cache

from lemminflect import getInflection
from spacy.tokens import Token

from app.core.nlp import get_nlp, zipf
from app.core.resources import load
from app.humanize.edits import local_rewrite
from app.humanize.text_utils import article_for
from app.humanize.types import Candidate, HumanizeContext, LocalEdit, SentenceView, make_candidate

TRANSFORM = "synonym"
POS_MAP = {"NOUN": "n", "VERB": "v", "ADJ": "a", "ADV": "r"}
MIN_ZIPF = 3.5
MIN_SIM = 0.45
MAX_SHARE = 0.15
PLAIN_GAIN = 1.0  # replacement must be ~10x more frequent to count as "plainer"
FORMAL_ZIPF = 4.0  # originals rarer than this are candidates for plainer words
# never swap these: auxiliaries, light verbs, quantity words, technical-ish function words
SKIP_LEMMAS = {
    "be",
    "have",
    "do",
    "get",
    "make",
    "go",
    "can",
    "will",
    "would",
    "should",
    "may",
    "might",
    "must",
    "use",
    "used",
    "show",
    "include",
    "also",
    "not",
    "very",
    "more",
    "most",
    "such",
    "other",
    "same",
    "first",
    "second",
    "third",
    "last",
    "new",
    "high",
    "low",
    "large",
    "small",
    "data",
    "value",
    "result",
    "system",
    "test",
    "figure",
    "table",
    "equation",
    "model",
    "method",
    "design",
    "current",
    "power",
    "energy",
    "force",
    "load",
    "stress",
    "strain",
    "voltage",
    "resistance",
    "temperature",
    "pressure",
    "speed",
    "rate",
    "time",
    "mass",
    "output",
    "input",
    "signal",
    "frequency",
    "circuit",
    "material",
    "sample",
    "error",
}


@lru_cache(maxsize=1)
def _abbrev() -> frozenset[str]:
    return frozenset(k.lower() for k in load("eng_abbreviations"))


@lru_cache(maxsize=65536)
def _vector_sim(a: str, b: str) -> float:
    vocab = get_nlp().vocab
    va, vb = vocab[a], vocab[b]
    if not (va.has_vector and vb.has_vector):
        return 0.0
    return float(va.similarity(vb))


LESK_TOP_SENSES = 2  # Lesk chooses among the word's most frequent senses only
CAND_TOP_SENSES = 3  # the shared sense must be a common sense of the candidate too
RELIABLE_VECTOR_ZIPF = 4.5  # en_core_web_md shares vectors between rare words


def _lesk_synset(context: list[str], word: str, pos: str):  # type: ignore[no-untyped-def]
    """Lesk over the word's most frequent senses; falls back to the most frequent sense."""
    from nltk.corpus import wordnet as wn
    from nltk.wsd import lesk

    synsets = wn.synsets(word, pos=pos)[:LESK_TOP_SENSES]
    if not synsets:
        return None
    try:
        syn = lesk(context, word, pos, synsets=synsets)
    except Exception:
        syn = None
    return syn or synsets[0]


@lru_cache(maxsize=65536)
def _common_sense(cand: str, synset_name: str, pos: str) -> bool:
    from nltk.corpus import wordnet as wn

    return any(s.name() == synset_name for s in wn.synsets(cand, pos=pos)[:CAND_TOP_SENSES])


def candidates_for(
    tok: Token, context: list[str], allow_hypernyms: bool = False
) -> list[tuple[str, float]]:
    """(lemma, zipf) of acceptable synonyms for a token, best (most frequent) first."""
    pos = POS_MAP.get(tok.pos_)
    if pos is None:
        return []
    lemma = tok.lemma_.lower()
    syn = _lesk_synset(context, lemma, pos)
    if syn is None:
        return []
    names = [ln.name() for ln in syn.lemmas()]
    # how often each lemma is used in this sense (SemCor counts): "improve" beats "better"
    sense_count = {ln.name().lower(): ln.count() for ln in syn.lemmas()}
    if pos == "n" and allow_hypernyms:
        for hyper in syn.hypernyms()[:1]:
            names += [ln.name() for ln in hyper.lemmas()]
    orig_z = zipf(lemma)
    own = {ln.name().lower() for ln in syn.lemmas()}
    out: dict[str, float] = {}
    for name in names:
        cand = name.lower()
        if "_" in cand or "-" in cand or cand == lemma or not cand.isalpha():
            continue
        if cand.startswith(lemma[:4]) and len(lemma) > 4:  # morphological variant, not a synonym
            continue
        z = zipf(cand)
        if z < MIN_ZIPF or z < orig_z - 0.5:
            continue
        if cand in own and not _common_sense(cand, syn.name(), pos):
            continue
        # vectors are only trustworthy for reasonably common words in the md model
        if min(orig_z, z) >= RELIABLE_VECTOR_ZIPF and _vector_sim(lemma, cand) < MIN_SIM:
            continue
        out[cand] = z
    return sorted(out.items(), key=lambda kv: (-sense_count.get(kv[0], 0), -kv[1]))


def inflect_like(lemma: str, tok: Token) -> str | None:
    tag = tok.tag_
    if tag in ("NN", "VB", "JJ", "RB", "VBP") or not tag:
        form = lemma
    else:
        out = getInflection(lemma, tag=tag)
        if not out:
            return None
        form = out[0]
    if tok.text[:1].isupper():
        form = form[:1].upper() + form[1:]
    return form


def _eligible(view: SentenceView, tok: Token) -> bool:
    return (
        tok.pos_ in POS_MAP
        and not tok.is_stop
        and tok.is_alpha
        and len(tok.text) > 2
        and tok.lemma_.lower() not in SKIP_LEMMAS
        and tok.lower_ not in _abbrev()
        and not tok.ent_type_
        and not (tok.text[:1].isupper() and tok.i != tok.sent.start)
        and not view.token_protected(tok)
    )


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    span = view.span
    eligible = [t for t in span if _eligible(view, t)]
    if not eligible:
        return []
    cap = max(1, int(len(eligible) * MAX_SHARE))
    swapped = ctx.swapped_lemmas.setdefault(view.sentence.paragraph, set())
    recent = set().union(*ctx.recent_lemmas[-2:]) if ctx.recent_lemmas else set()
    context = [t.lower_ for t in span if t.is_alpha]
    from app.humanize.transforms.phrase_simplify import document_hits

    phrase_hits = [h for h in document_hits(ctx) if view.start <= h.start < view.sentence.end]

    proposals: list[tuple[float, LocalEdit]] = []
    for tok in eligible:
        lemma = tok.lemma_.lower()
        if lemma in swapped:
            continue
        repeated = lemma in recent
        orig_z = zipf(lemma)
        if not repeated and orig_z >= FORMAL_ZIPF:
            continue
        # nouns in reports are terminology: repeating them keeps meaning exact, so never swap
        if tok.pos_ == "NOUN":
            continue
        # words inside a known stock/wordy phrase are handled by phrase_simplify
        s0, e0 = view.local(tok)
        if any(h.start <= view.start + s0 and view.start + e0 <= h.end for h in phrase_hits):
            continue
        for cand, z in candidates_for(tok, context, allow_hypernyms=repeated):
            if not repeated and z < orig_z + PLAIN_GAIN:
                continue
            form = inflect_like(cand, tok)
            if not form:
                continue
            s, e = view.local(tok)
            repl = form
            # a/an agreement with the previous word
            prev = tok.nbor(-1) if tok.i > span.start else None
            if prev is not None and prev.lower_ in ("a", "an") and tok.i - 1 >= span.start:
                want = article_for(form)
                if want != prev.lower_:
                    s = prev.idx - view.start
                    art = want.capitalize() if prev.text[0].isupper() else want
                    repl = f"{art} {form}"
            key = "transform.synonym.repeat" if repeated else "transform.synonym"
            ed = local_rewrite(view.text, s, e, repl, TRANSFORM, key, old=tok.text, new=form)
            if ed is not None:
                gain = (z - orig_z) + (1.0 if repeated else 0.0)
                proposals.append((gain, ed))
            break
    if not proposals:
        return []
    proposals.sort(key=lambda p: -p[0])
    picked = [ed for _, ed in proposals[:cap]]
    out: list[Candidate] = []
    full = make_candidate(view, picked, (TRANSFORM,))
    if full:
        out.append(full)
    if len(picked) > 1:
        for ed in picked[:2]:
            c = make_candidate(view, [ed], (TRANSFORM,))
            if c:
                out.append(c)
    return out


def record_swaps(ctx: HumanizeContext, paragraph: int, cand: Candidate, view: SentenceView) -> None:
    """Remember swapped lemmas so a lemma is only swapped once per paragraph."""
    swapped = ctx.swapped_lemmas.setdefault(paragraph, set())
    for ed in cand.edits:
        if ed.transform != TRANSFORM:
            continue
        for tok in view.span:
            s, e = view.local(tok)
            if ed.start <= s and e <= ed.end:
                swapped.add(tok.lemma_.lower())
