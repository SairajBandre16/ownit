"""passive_to_active: rebuild a passive sentence with an explicit agent in the active voice.

"The data was processed by the controller in real time."
    -> "The controller processed the data in real time."

Only when an explicit agent exists (agent -> pobj). The verb is conjugated to the agent's
number and the original tense (lemminflect). Skipped in Methodology sections, where passive
voice is conventional. This is one of the riskiest transforms, so it bails out on anything
unusual (coordination, relative clauses inside the subject, questions, multiple passives).
"""

from __future__ import annotations

from lemminflect import getInflection
from spacy.tokens import Span, Token

from app.humanize.edits import edits_from_rewrite
from app.humanize.text_utils import capitalize_first
from app.humanize.types import Candidate, HumanizeContext, SentenceView, make_candidate

TRANSFORM = "passive_to_active"
SUBJ_TO_OBJ = {"i": "me", "he": "him", "she": "her", "we": "us", "they": "them", "who": "whom"}
OBJ_TO_SUBJ = {v: k for k, v in SUBJ_TO_OBJ.items() if k != "who"} | {"me": "I"}
MODALS = {"can", "could", "will", "would", "shall", "should", "may", "might", "must"}


def _text(tokens: list[Token]) -> str:
    """Original spacing of a contiguous token list."""
    if not tokens:
        return ""
    doc = tokens[0].doc
    return doc[tokens[0].i : tokens[-1].i + 1].text


def _is_plural(tok: Token) -> bool:
    if tok.lower_ in ("they", "we", "you", "i", "them", "us"):
        return tok.lower_ != "i"
    if any(c.dep_ == "cc" for c in tok.children) and any(c.dep_ == "conj" for c in tok.children):
        return True
    return tok.tag_ in ("NNS", "NNPS")


def _agent_phrase(pobj: Token) -> str:
    toks = list(pobj.subtree)
    text = _text(toks)
    if len(toks) == 1 and pobj.lower_ in OBJ_TO_SUBJ:
        text = OBJ_TO_SUBJ[pobj.lower_]
    return text


def _patient_phrase(subj: Token) -> str:
    toks = list(subj.subtree)
    text = _text(toks)
    if len(toks) == 1 and subj.lower_ in SUBJ_TO_OBJ:
        return SUBJ_TO_OBJ[subj.lower_]
    first = toks[0]
    if first.pos_ != "PROPN" and not first.text.isupper() and first.text != "I":
        text = text[:1].lower() + text[1:]
    return text


def _verb_group(verb: Token, plural: bool) -> str | None:
    """Active verb group for the passive's tense/aspect."""
    auxes = [c for c in verb.children if c.dep_ in ("aux", "auxpass") and c.i < verb.i]
    lemmas = [a.lower_ for a in auxes]
    lemma = verb.lemma_.lower()

    def infl(tag: str) -> str | None:
        out = getInflection(lemma, tag=tag)
        return out[0] if out else None

    modal = next((a for a in lemmas if a in MODALS), None)
    if modal:
        if "have" in lemmas and "been" in lemmas:  # "could have been measured"
            vbn = infl("VBN")
            return f"{modal} have {vbn}" if vbn else None
        return f"{modal} {lemma}"
    if "being" in lemmas:  # progressive: "is being tested"
        be_aux = [a for a in auxes if a.lemma_ == "be" and a.lower_ != "being"]
        if not be_aux:
            return None
        be = be_aux[0]
        vbg = infl("VBG")
        if not vbg:
            return None
        if be.tag_ == "VBD":
            return f"{'were' if plural else 'was'} {vbg}"
        return f"{'are' if plural else 'is'} {vbg}"
    if "been" in lemmas:  # perfect: "has been measured"
        have = next((a for a in auxes if a.lemma_ == "have"), None)
        if have is None:
            return None
        vbn = infl("VBN")
        if not vbn:
            return None
        if have.tag_ == "VBD":
            return f"had {vbn}"
        return f"{'have' if plural else 'has'} {vbn}"
    passive_aux = [a for a in auxes if a.dep_ == "auxpass"]
    if not passive_aux:
        return None
    be = passive_aux[0]
    if be is None:
        return None
    if be.tag_ == "VBD" or be.lower_ in ("was", "were"):
        return infl("VBD")
    if be.lower_ in ("is", "are", "am"):
        return infl("VBP") if plural else infl("VBZ")
    return None


def rewrite(span: Span) -> str | None:
    passives = [t for t in span if t.dep_ == "auxpass"]
    if len(passives) != 1:
        return None
    verb = passives[0].head
    if verb.dep_ not in ("ROOT",) or verb.pos_ != "VERB":
        return None
    subj = next((c for c in verb.children if c.dep_ == "nsubjpass"), None)
    agent = next((c for c in verb.children if c.dep_ == "agent"), None)
    if subj is None or agent is None:
        return None
    pobj = next((c for c in agent.children if c.dep_ == "pobj"), None)
    if pobj is None or any(c.dep_ == "conj" for c in verb.children):
        return None
    if span.text.rstrip().endswith("?"):
        return None
    subj_toks = list(subj.subtree)
    if any(t.dep_ in ("relcl", "acl") for t in subj_toks):
        return None
    agent_toks = list(agent.subtree)
    aux_toks = [c for c in verb.children if c.dep_ in ("aux", "auxpass", "neg") and c.i < verb.i]
    if any(t.dep_ == "neg" for t in aux_toks):
        return None
    group = _verb_group(verb, _is_plural(pobj))
    if not group:
        return None
    used = {t.i for t in subj_toks + agent_toks + aux_toks + [verb]}
    content = [t for t in span if not (t.is_space)]
    final_punct = (
        content[-1] if content and content[-1].is_punct and content[-1].text in ".!" else None
    )
    if final_punct is not None:
        used.add(final_punct.i)
    prefix = [t for t in content if t.i < subj_toks[0].i and t.i not in used]
    rest = [t for t in content if t.i > subj_toks[0].i and t.i not in used]
    # the rest must be contiguous chunks; rebuild them with original spacing
    rest_text = " ".join(_chunks(rest))
    prefix_text = _text(prefix) if prefix else ""
    agent_text = _agent_phrase(pobj)
    if prefix_text:
        # mid-sentence now: keep names/acronyms/"I" capitalised, lower-case anything else
        first_word = agent_text.split()[0]
        keep = pobj.pos_ == "PROPN" or first_word.isupper()
        agent_text = agent_text if keep else agent_text[:1].lower() + agent_text[1:]
    parts = [p for p in (prefix_text, agent_text, group, _patient_phrase(subj), rest_text) if p]
    out = " ".join(parts)
    out = out.replace(" ,", ",").replace("  ", " ")
    out = capitalize_first(out) + (final_punct.text if final_punct is not None else "")
    return out


def _chunks(tokens: list[Token]) -> list[str]:
    """Group consecutive tokens and return their original text."""
    groups: list[list[Token]] = []
    for t in tokens:
        if groups and t.i == groups[-1][-1].i + 1:
            groups[-1].append(t)
        else:
            groups.append([t])
    return [_text(g) for g in groups]


def apply(view: SentenceView, ctx: HumanizeContext) -> list[Candidate]:
    if view.sentence.section == "methodology":
        return []
    new = rewrite(view.span)
    if not new or new == view.text:
        return []
    subj = next((t for t in view.span if t.dep_ == "nsubjpass"), None)
    agent = next((t for t in view.span if t.dep_ == "pobj" and t.head.dep_ == "agent"), None)
    edits = edits_from_rewrite(
        view.text,
        new,
        TRANSFORM,
        "transform.passive_to_active",
        agent=_agent_phrase(agent) if agent is not None else "the agent",
    )
    if not edits or subj is None:
        return []
    c = make_candidate(view, edits, (TRANSFORM,))
    return [c] if c else []
