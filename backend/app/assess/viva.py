"""Viva questions and the adaptive Viva Simulator (CLAUDE.md §9.4, U3).

Templates (resources/question_templates.json) are filled from the dependency parse of key
sentences:
  definition   "What is {X}?"                       definition sentences, top concepts
  effect       "How does {subj} affect {obj}?"       effect verbs with subject + object
  method       "How did you {verb} {obj}?"           Methodology sentences
  choice       "Why did you choose {X}?"             "X was used/selected …"
  causal       "Why …?"                              because / due to / therefore
  result_value "What does the value {v} tell you?"   Results sentences with a number + unit
  comparison   "What is the difference between …?"  compared with / than / unlike …
  evaluate     "What are the limitations of {X}?"    central concepts

Ladder: 1 define → 2 how → 3 why → 4 compare/evaluate. After an answer: score ≥ 70 → one level
up on a new concept; score < 40 → back to a definition of the concept that was missed;
otherwise the same level on a new concept. Ten questions per session.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from spacy.tokens import Doc, Token

from app.assess.concepts import body_text, doc_keyphrases, span_concepts
from app.assess.keysent import KeySentence, key_sentences
from app.assess.types import Question
from app.core.nlp import parse, zipf
from app.core.protect import _unit_re
from app.core.resources import load
from app.core.segment import Segmentation

SESSION_LENGTH = 10
TECH_ZIPF = 3.8  # single words rarer than this are technical enough to define
UP, DOWN = 70, 40
MAX_NP_TOKENS = 7
MIN_Q_WORDS, MAX_Q_WORDS = 4, 26
HEDGE_MODALS = {"may", "might", "could", "would"}
HEDGE_WORDS = {
    "likely",
    "probably",
    "possibly",
    "perhaps",
    "maybe",
    "mainly",
    "mostly",
    "partly",
    "largely",
    "also",
}
EMPTY_NOUNS = {"way", "thing", "life", "world", "people", "aspect", "manner", "lot", "kind", "fact"}
TRAILING_CLAUSE = re.compile(r",\s+(?:which|where|making|resulting|thereby|leading)\b")
# evaluate questions ("limitations of X") suit things and methods, not quantities or events
EVALUABLE_LEXNAMES = {
    "noun.artifact",
    "noun.substance",
    "noun.act",
    "noun.process",
    "noun.cognition",
}
PRONOUN_SWAP = {
    "we": "you",
    "our": "your",
    "us": "you",
    "i": "you",
    "my": "your",
    "me": "you",
    "ours": "yours",
}


@lru_cache(maxsize=1)
def templates() -> dict[str, Any]:
    return load("question_templates")  # type: ignore[no-any-return]


def level_name(level: int) -> str:
    return str(templates()["levels"][str(level)])


def _pick(kind: str, key: str) -> tuple[str, int]:
    t = templates()["templates"][kind]
    prompts = t["prompts"]
    h = int(hashlib.sha1(key.encode()).hexdigest(), 16)
    return prompts[h % len(prompts)], int(t["level"])


# ---------------------------------------------------------------- phrase helpers
def _is_proper(tok: Token) -> bool:
    return tok.pos_ == "PROPN" or (len(tok.text) > 1 and tok.text[1:2].isupper())


def phrase(tok: Token, keep_det: bool = True, keep_acl: bool = False) -> str | None:
    """Text of the noun phrase headed by `tok` (no relative clauses), lower-cased at the start
    unless it's a name. None for pronouns (except we/I) and long phrases. `keep_acl` keeps a
    participle modifier ("the values predicted by the correlation")."""
    if tok.pos_ == "PRON" and tok.lower_ not in ("we", "i"):
        return None
    drop: set[int] = set()
    cut = ("relcl", "appos", "advcl") if keep_acl else ("relcl", "acl", "appos", "advcl")
    for c in tok.children:
        if c.dep_ in cut:
            drop |= {t.i for t in c.subtree}
    toks = [t for t in tok.subtree if t.i not in drop]
    for k, t in enumerate(toks):
        if t.text == "(":
            toks = toks[:k]
            break
    while toks and toks[-1].is_punct:
        toks.pop()
    if not keep_det:
        while toks and toks[0].pos_ == "DET":
            toks = toks[1:]
    if not toks or len(toks) > MAX_NP_TOKENS:
        return None
    text = "".join(t.text_with_ws for t in toks).strip()
    words = text.split()
    words = [PRONOUN_SWAP.get(w.lower(), w) if w.lower() in PRONOUN_SWAP else w for w in words]
    text = " ".join(words)
    if not _is_proper(toks[0]) and text[:1].isupper() and toks[0].lower_ not in PRONOUN_SWAP:
        text = text[0].lower() + text[1:]
    return text


def _plural(tok: Token) -> bool:
    return tok.tag_ in ("NNS", "NNPS") or any(c.dep_ == "conj" for c in tok.children)


def _swap_pronouns(text: str) -> str:
    return re.sub(
        r"\b(we|our|us|I|my|me|ours)\b",
        lambda m: PRONOUN_SWAP[m.group(1).lower()],
        text,
        flags=re.IGNORECASE,
    )


def _finish(q: str) -> str | None:
    q = re.sub(r"\s+", " ", q).strip()
    q = re.sub(r"\s+([,.;:?])", r"\1", q)
    q = q[0].upper() + q[1:] if q else q
    n = len(q.split())
    if not (MIN_Q_WORDS <= n <= MAX_Q_WORDS):
        return None
    return q


def why_question(text: str) -> str | None:
    """Turn a declarative main clause into a why-question with do-support:
    "the pump stopped" → "Why did the pump stop?"."""
    doc: Doc = parse(text.strip().rstrip(".!,;: "))
    root = next((t for t in doc if t.dep_ == "ROOT"), None)
    if root is None or root.pos_ not in ("VERB", "AUX"):
        return None
    subj = next(
        (c for c in root.children if c.dep_ in ("nsubj", "nsubjpass") and c.i < root.i), None
    )
    if subj is None or any(c.dep_ == "neg" for c in root.children):
        return None
    subj_text = phrase(subj)
    if subj_text is None:
        return None
    subj_toks = {t.i for t in subj.subtree}
    # anything before the subject (other than punctuation) makes the reordering unsafe
    if any(t.i < min(subj_toks) and not t.is_punct for t in doc):
        return None
    auxes = [c for c in root.children if c.dep_ in ("aux", "auxpass") and c.i < root.i]
    if auxes and auxes[0].lower_ in HEDGE_MODALS:
        return None  # "Why may this discrepancy be …?" asks about a guess
    middle = [t for t in doc if max(subj_toks) < t.i < root.i and t not in auxes]
    rest = doc[root.i + 1 :].text if root.i + 1 < len(doc) else ""
    rest = TRAILING_CLAUSE.split(rest, maxsplit=1)[0]  # drop ", which is a testament to …"
    # "Our value is likely [due to …]" leaves nothing to ask about once the cause is removed
    content = [w for w in re.findall(r"[\w-]+", rest.lower()) if w not in HEDGE_WORDS]
    if root.lemma_ == "be" and not content:
        return None
    mid = " ".join(t.text for t in middle)
    if auxes:
        first, others = auxes[0], auxes[1:]
        verb_group = " ".join([t.text for t in others] + [mid, root.text])
        q = f"Why {first.lower_} {subj_text} {verb_group} {rest}"
    elif root.lemma_ == "be":
        q = f"Why {root.lower_} {subj_text} {mid} {rest}"
    else:
        do = {"VBD": "did", "VBZ": "does", "VBP": "do"}.get(root.tag_)
        if do is None:
            return None
        q = f"Why {do} {subj_text} {mid} {root.lemma_.lower()} {rest}"
    q = _swap_pronouns(q.rstrip(" ,;:")) + "?"
    return _finish(q)


# ---------------------------------------------------------------- generators
@dataclass
class Draft:
    kind: str
    prompt: str
    target: str  # the concept the question is about


def _root(doc: Doc) -> Token | None:
    return next((t for t in doc if t.dep_ == "ROOT"), None)


def _verb_lemma(v: Token) -> str:
    prt = next((c for c in v.children if c.dep_ == "prt"), None)
    return v.lemma_.lower() + (f" {prt.lower_}" if prt is not None else "")


def effect_q(doc: Doc) -> Draft | None:
    verbs = set(templates()["effect_verbs"])
    for v in doc:
        if v.pos_ != "VERB" or v.lemma_.lower() not in verbs:
            continue
        subj = next((c for c in v.children if c.dep_ == "nsubj"), None)
        obj = next((c for c in v.children if c.dep_ == "dobj"), None)
        agent = next((c for c in v.children if c.dep_ == "agent"), None)
        patient = next((c for c in v.children if c.dep_ == "nsubjpass"), None)
        if agent is not None and patient is not None:
            pobj = next((c for c in agent.children if c.dep_ == "pobj"), None)
            subj, obj = pobj, patient
        if subj is None or obj is None:
            continue
        s, o = phrase(subj), phrase(obj)
        if not s or not o or s.lower() in ("you", "it") or s.lower() == o.lower():
            continue
        if obj.lemma_.lower() in EMPTY_NOUNS or subj.lemma_.lower() in EMPTY_NOUNS:
            continue  # "affect the way [we live]" means nothing without its clause
        tmpl, _ = _pick("effect", doc.text)
        q = tmpl.replace("{subj}", s).replace("{obj}", o)
        if _plural(subj):
            q = q.replace("How does", "How do").replace(" changes ", " change ")
        out = _finish(q)
        if out:
            return Draft("effect", out, phrase(subj, keep_det=False) or s)
    return None


def method_q(doc: Doc) -> Draft | None:
    root = _root(doc)
    skip = set(templates()["method_skip_verbs"])
    if (
        root is None
        or root.pos_ != "VERB"
        or root.lemma_.lower() in skip
        or root.tag_ not in ("VBD", "VBN")
    ):
        return None
    patient = next((c for c in root.children if c.dep_ == "nsubjpass"), None)
    subj = next((c for c in root.children if c.dep_ == "nsubj"), None)
    obj = None
    if patient is not None:
        obj = patient
    elif subj is not None and subj.lower_ in ("we", "i"):
        obj = next((c for c in root.children if c.dep_ == "dobj"), None)
    if obj is None or obj.pos_ == "PRON":
        return None
    o = phrase(obj)
    if not o:
        return None
    if o.lower().startswith(("a ", "an ")):
        o = "the " + o.split(" ", 1)[1]
    tmpl, _ = _pick("method", doc.text)
    out = _finish(tmpl.replace("{verb}", _verb_lemma(root)).replace("{obj}", o))
    return Draft("method", out, phrase(obj, keep_det=False) or o) if out else None


def choice_q(doc: Doc) -> Draft | None:
    verbs = set(templates()["choice_verbs"])
    for v in doc:
        if v.pos_ != "VERB" or v.lemma_.lower() not in verbs:
            continue
        x = next((c for c in v.children if c.dep_ == "nsubjpass"), None)
        if x is None:
            subj = next((c for c in v.children if c.dep_ == "nsubj"), None)
            if subj is not None and subj.lower_ in ("we", "i"):
                x = next((c for c in v.children if c.dep_ == "dobj"), None)
        if x is None or x.pos_ == "PRON":
            continue
        text = phrase(x)
        if not text:
            continue
        tmpl, _ = _pick("choice", doc.text)
        out = _finish(tmpl.replace("{X}", text))
        if out:
            return Draft("choice", out, phrase(x, keep_det=False) or text)
    return None


def causal_q(doc: Doc) -> Draft | None:
    t = templates()
    text = doc.text
    # "Therefore, X." / "As a result, X."
    for c in t["result_connectors"]:
        m = re.match(rf"\s*{re.escape(c)}\s*,?\s+", text, re.IGNORECASE)
        if m:
            q = why_question(text[m.end() :])
            return Draft("causal", q, "") if q else None
    # "X due to Y." / "X because of Y."
    for p in t["causal_preps"]:
        m = re.search(rf",?\s+{re.escape(p)}\b", text, re.IGNORECASE)
        if m and len(text[: m.start()].split()) >= 4:
            q = why_question(text[: m.start()])
            return Draft("causal", q, "") if q else None
    # "X because Y." / "Because Y, X."
    root = _root(doc)
    if root is None:
        return None
    for adv in root.children:
        mark = next(
            (c for c in adv.children if c.dep_ == "mark" and c.lower_ in t["causal_marks"]), None
        )
        if adv.dep_ != "advcl" or mark is None:
            continue
        sub = sorted(adv.subtree, key=lambda x: x.i)
        lo, hi = sub[0].idx, sub[-1].idx + len(sub[-1])
        main = (text[:lo] + text[hi:]).strip(" ,.")
        q = why_question(main)
        return Draft("causal", q, "") if q else None
    return None


def result_value_q(doc: Doc, section: str) -> Draft | None:
    if section not in ("results", "discussion"):
        return None
    m = _unit_re().search(doc.text)
    if not m:
        return None
    value = m.group().strip()
    root = _root(doc)
    subj = (
        next((c for c in root.children if c.dep_ in ("nsubj", "nsubjpass")), None)
        if root is not None
        else None
    )
    s = phrase(subj) if subj is not None else None
    prompts = templates()["templates"]["result_value"]["prompts"]
    if subj is not None and s and value not in s and s.lower() not in ("you", "it", "this"):
        out = _finish(prompts[0].replace("{value}", value).replace("{subj}", s))
        target = phrase(subj, keep_det=False) or s
    else:
        out = _finish(prompts[1].replace("{value}", value))
        target = ""
    return Draft("result_value", out, target) if out else None


def comparison_q(doc: Doc) -> Draft | None:
    text = doc.text
    markers = templates()["comparison_markers"]
    for mk in markers:
        m = re.search(rf"\b{re.escape(mk)}\b", text, re.IGNORECASE)
        if not m:
            continue
        after = [c for c in doc.noun_chunks if c.start_char >= m.end()]
        if (
            not after
            or after[0].root.pos_ not in ("NOUN", "PROPN")
            or after[0].start_char - m.end() > 2
        ):
            continue
        b_tok = after[0].root
        root = _root(doc)
        a_tok = None
        if (mk.lower() in ("unlike",) and root is not None) or root is not None:
            a_tok = next((c for c in root.children if c.dep_ in ("nsubj", "nsubjpass")), None)
        if a_tok is None:
            continue
        a, b = phrase(a_tok), phrase(b_tok, keep_acl=True)
        if not a or not b or a.lower() == b.lower() or a.lower() in ("you", "it"):
            continue
        if b_tok.like_num or any(t.like_num for t in after[0]):
            continue
        tmpl, _ = _pick("comparison", text)
        out = _finish(tmpl.replace("{A}", a).replace("{B}", b))
        if out:
            return Draft("comparison", out, phrase(a_tok, keep_det=False) or a)
    return None


# ---------------------------------------------------------------- the bank
def _qid(kind: str, start: int, prompt: str) -> str:
    return f"v-{kind}-{start}-{hashlib.sha1(prompt.encode()).hexdigest()[:6]}"


def _question(
    seg: Segmentation, kind: str, prompt: str, target: str, start: int, end: int, level: int
) -> Question:
    concepts = span_concepts(seg, start, end, limit=5, exclude=prompt)
    if kind == "evaluate":
        concepts = [target, *(c for c in concepts if c.lower() != target.lower())][:4]
    return Question(
        id=_qid(kind, start, prompt),
        type="viva",
        prompt=prompt,
        answer_key=seg.text[start:end].strip(),
        source_start=start,
        source_end=end,
        concepts=concepts,
        explanation=seg.text[start:end].strip(),
        level=level,
        kind=kind,
        target=target,
    )


def _first_mention(keys: list[KeySentence], concept: str) -> KeySentence | None:
    pat = re.compile(rf"(?<![\w-]){re.escape(concept)}(?![\w-])", re.IGNORECASE)
    hits = [k for k in keys if pat.search(k.sent.text)]
    if not hits:
        return None
    defs = [k for k in hits if k.definition and k.definition.term.lower() == concept.lower()]
    return defs[0] if defs else max(hits[:3], key=lambda k: k.score)


def evaluable(concept: str) -> bool:
    """A device, material or method (WordNet sense of its head word), or an abbreviation."""
    from nltk.corpus import wordnet as wn

    from app.assess.mcq import _is_abbr

    if _is_abbr(concept):
        return True
    doc = parse(concept)
    head = next((t for t in doc if t.dep_ == "ROOT"), None)
    if head is None or head.pos_ not in ("NOUN", "PROPN"):
        return False
    synsets = wn.synsets(head.lemma_.lower(), pos=wn.NOUN)[:1]  # the usual sense only
    return any(s.lexname() in EVALUABLE_LEXNAMES for s in synsets)


def concept_phrase(concept: str, seg: Segmentation) -> tuple[str, bool]:
    """How to name a concept in a question, and whether it is plural: keeps its case as used
    in the text ("Internet of Things", "water scarcity") and the article the text gives it
    ("the smart irrigation controller", "a PLC")."""
    from app.assess.cloze import display_form
    from app.humanize.text_utils import article_for

    shown = display_form(concept, seg.text)
    doc = parse(shown)
    head = next((t for t in doc if t.dep_ == "ROOT"), None)  # "Internet" in "Internet of Things"
    plural = head is not None and head.tag_ in ("NNS", "NNPS")
    # "the proposed solar tracking system" still tells us the concept takes "the"
    m = re.search(
        rf"\b(the|a|an|our|my)\s+(?:[\w-]+\s+)?{re.escape(concept)}(?![\w-])",
        body_text(seg),
        flags=re.IGNORECASE,
    )
    if m and (not plural or m.group(1).lower() in ("the", "our", "my")):
        det = m.group(1).lower()
        if det in ("a", "an"):
            det = article_for(shown)
        elif det in ("our", "my"):
            det = "your"
        shown = f"{det} {shown}"
    return shown, plural


def definition_question(
    seg: Segmentation, keys: list[KeySentence], concept: str
) -> Question | None:
    ks = _first_mention(keys, concept)
    if ks is None:
        return None
    from app.assess.mcq import _is_abbr

    kind = "abbreviation" if _is_abbr(concept) else "definition"
    tmpl, level = _pick(kind, concept)
    shown, plural = concept_phrase(concept, seg)
    if kind == "abbreviation":
        shown = concept
    elif plural:
        tmpl = tmpl.replace("What is", "What are").replace("What does", "What do")
    prompt = _finish(tmpl.replace("{X}", shown))
    if not prompt:
        return None
    # a definition answer should cover what the source sentence says about the concept
    s = ks.sent
    return _question(seg, kind, prompt, concept, s.start, s.end, level)


def build_bank(seg: Segmentation) -> list[Question]:
    if "assess.viva_bank" in seg.cache:
        return seg.cache["assess.viva_bank"]  # type: ignore[no-any-return]
    keys = key_sentences(seg)
    bank: list[Question] = []
    seen_prompts: set[str] = set()

    def add(q: Question | None) -> None:
        if q is not None and q.prompt.lower() not in seen_prompts:
            seen_prompts.add(q.prompt.lower())
            bank.append(q)

    concepts = doc_keyphrases(seg)[:12]
    defined = {k.definition.term.lower() for k in keys if k.definition}
    for c in concepts:
        # "farmers", "crops": everyday words make poor definition questions
        if c.lower() in defined or len(c.split()) >= 2 or c.isupper() or zipf(c) < TECH_ZIPF:
            add(definition_question(seg, keys, c))
    for ks in sorted(keys, key=lambda k: -k.score)[:60]:
        doc, s = ks.doc, ks.sent
        drafts = [
            effect_q(doc),
            method_q(doc) if s.section == "methodology" else None,
            choice_q(doc),
            causal_q(doc),
            result_value_q(doc, s.section),
            comparison_q(doc),
        ]
        for d in drafts:
            if d is None or not d.prompt:
                continue
            _, level = _pick(d.kind, d.prompt)
            add(_question(seg, d.kind, d.prompt, d.target, s.start, s.end, level))
    for c in [c for c in concepts if evaluable(c)][:3]:
        first = _first_mention(keys, c)
        if first is None:
            continue
        tmpl, level = _pick("evaluate", c)
        prompt = _finish(tmpl.replace("{X}", concept_phrase(c, seg)[0]))
        if prompt:
            add(_question(seg, "evaluate", prompt, c, first.sent.start, first.sent.end, level))
    seg.cache["assess.viva_bank"] = bank
    return bank


# ---------------------------------------------------------------- adaptive session
@dataclass
class Turn:
    question: str
    answer: str
    score: float
    id: str | None = None
    missed_concepts: list[str] | None = None


def next_question(seg: Segmentation, history: list[Turn]) -> Question | None:
    """The next viva question for this session, or None when the session is over."""
    if len(history) >= SESSION_LENGTH:
        return None
    bank = build_bank(seg)
    if not bank:
        return None
    asked = {t.question.strip().lower() for t in history}
    by_id = {q.id: q for q in bank}
    by_prompt = {q.prompt.lower(): q for q in bank}
    asked_targets = {
        (
            by_id.get(t.id or "")
            or by_prompt.get(t.question.strip().lower())
            or Question("", "viva", "", "", 0, 0)
        ).target
        for t in history
    }
    fresh = [q for q in bank if q.prompt.lower() not in asked]

    def at_level(level: int, new_concept: bool = True) -> Question | None:
        for lv in [level, *sorted({1, 2, 3, 4} - {level}, key=lambda x: (abs(x - level), -x))]:
            pool = [q for q in fresh if q.level == lv]
            if new_concept:
                pool = [q for q in pool if not q.target or q.target not in asked_targets] or pool
            if pool:
                return pool[0]
        return None

    if not history:
        return at_level(1)
    last = history[-1]
    last_q = by_id.get(last.id or "") or by_prompt.get(last.question.strip().lower())
    level = last_q.level if last_q and last_q.level else 1
    if last.score >= UP:
        return at_level(min(4, level + 1))
    if last.score < DOWN:
        missed = list(last.missed_concepts or []) or (last_q.concepts if last_q else [])
        if last_q and last_q.target:
            missed = [last_q.target, *missed] if level > 1 else missed
        keys = key_sentences(seg)
        for concept in missed:
            q = definition_question(seg, keys, concept)
            if q is not None and q.prompt.lower() not in asked:
                return q
        return at_level(1)
    return at_level(level)
