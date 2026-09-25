"""Phrase lexicon matching with light inflection support.

Lexicon keys are lowercase phrases. A `{lemma}` placeholder matches every inflection of that
verb (e.g. "{play} a crucial role" matches "plays/played/playing a crucial role"). Replacement
templates may use `{lemma}` too; it is re-inflected to the tense that was matched
("made a decision" -> "decided").
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

from lemminflect import getAllInflections, getInflection
from spacy.tokens import Doc

_PLACEHOLDER = re.compile(r"\{([a-z]+)\}")


@dataclass(frozen=True)
class LexMatch:
    start: int
    end: int
    key: str  # lexicon key that matched
    text: str  # matched surface text
    tag: str | None  # Penn tag of the inflected placeholder, if any
    value: Any
    plural_subject: bool = False


def verb_forms(lemma: str) -> dict[str, str]:
    """{surface: penn_tag} for all inflections of a verb lemma."""
    forms: dict[str, str] = {lemma: "VB"}
    infl = getAllInflections(lemma, upos="VERB")
    for tag, words in infl.items():
        for w in words:
            forms.setdefault(w, tag)
    if "VBN" not in infl and "VBD" in infl:
        pass  # VBD form already present; VBN identical for regular verbs
    return forms


def inflect(lemma: str, tag: str | None, plural: bool = False) -> str:
    if not tag or tag == "VB":
        return lemma
    if lemma == "be":
        if tag == "VBP":
            return "are"
        if tag == "VBD":
            return "were" if plural else "was"
    out = getInflection(lemma, tag=tag)
    if not out and tag == "VBN":
        out = getInflection(lemma, tag="VBD")
    return out[0] if out else lemma


def match_case(template: str, source: str) -> str:
    """Give `template` the capitalisation style of `source`."""
    if not template:
        return template
    if source.isupper() and len(source) > 1:
        return template.upper()
    if source[:1].isupper():
        return template[:1].upper() + template[1:]
    return template


def _context_tag(doc: Doc, offset: int, fallback: str) -> tuple[str, bool]:
    """Penn tag of the verb at `offset` and whether its subject is plural."""
    span = doc.char_span(offset, offset + 1, alignment_mode="expand")
    if span is None or not len(span):
        return fallback, False
    tok = span[0]
    subj = next((c for c in tok.children if c.dep_ in ("nsubj", "nsubjpass")), None)
    if subj is None and tok.dep_ in ("xcomp", "conj"):
        subj = next((c for c in tok.head.children if c.dep_ in ("nsubj", "nsubjpass")), None)
    plural = subj is not None and (
        subj.tag_ in ("NNS", "NNPS")
        or subj.lower_ in ("we", "they", "you")
        or any(c.dep_ == "conj" for c in subj.children)
    )
    return (tok.tag_ if tok.tag_.startswith("VB") else fallback), plural


class PhraseLexicon:
    def __init__(self, entries: Mapping[str, Any]) -> None:
        self.entries = dict(entries)
        self._surface: dict[str, tuple[str, str | None]] = {}
        for key in self.entries:
            for surface, tag in self._expand(key):
                self._surface.setdefault(surface, (key, tag))
        alts = sorted(self._surface, key=len, reverse=True)
        pattern = "|".join(self._to_regex(s) for s in alts)
        self._re = (
            re.compile(rf"(?<![\w\-])(?:{pattern})(?![\w\-])", re.IGNORECASE) if alts else None
        )

    @staticmethod
    def _expand(key: str) -> list[tuple[str, str | None]]:
        m = _PLACEHOLDER.search(key)
        if not m:
            return [(key.lower(), None)]
        out: list[tuple[str, str | None]] = []
        for form, tag in verb_forms(m.group(1)).items():
            out.append((key[: m.start()] + form + key[m.end() :], tag))
        return out

    @staticmethod
    def _to_regex(surface: str) -> str:
        parts = []
        for word in surface.split():
            parts.append(re.sub(r"['’]", "['’]", re.escape(word)))
        return r"\s+".join(parts)

    def find(self, text: str, doc: Doc | None = None) -> list[LexMatch]:
        """Non-overlapping matches, longest first. Pass the spaCy `doc` of `text` to resolve
        ambiguous verb forms from context ("play" VB vs VBP, "made" VBD vs VBN)."""
        if self._re is None:
            return []
        out = []
        for m in self._re.finditer(text):
            norm = " ".join(m.group().lower().replace("’", "'").split())
            hit = self._surface.get(norm)
            if hit is None:
                continue
            key, tag = hit
            plural = False
            if tag is not None and doc is not None:
                tag, plural = _context_tag(doc, m.start(), tag)
            out.append(LexMatch(m.start(), m.end(), key, m.group(), tag, self.entries[key], plural))
        return out

    @staticmethod
    def render(template: str, match: LexMatch) -> str:
        """Fill a replacement template for a match (inflection + capitalisation)."""
        filled = _PLACEHOLDER.sub(
            lambda m: inflect(m.group(1), match.tag, match.plural_subject), template
        )
        return match_case(filled, match.text)


@cache
def lexicon(name: str) -> PhraseLexicon:
    """Build a PhraseLexicon from a resource file.

    Dict resources map phrase -> value. List resources are either strings or objects with a
    "phrase" field.
    """
    from app.core.resources import load

    data = load(name)
    if isinstance(data, dict):
        entries = {k.lower(): v for k, v in data.items() if not k.startswith("_")}
    else:
        entries = {}
        for item in data:
            if isinstance(item, str):
                entries[item.lower()] = None
            else:
                entries[item["phrase"].lower()] = item
    return PhraseLexicon(entries)
