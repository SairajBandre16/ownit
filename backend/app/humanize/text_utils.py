"""Small string helpers used by transforms: capitalisation and a/an agreement."""

from __future__ import annotations

import re

_AN_EXCEPTIONS_A = ("uni", "use", "usu", "ute", "uti", "one", "once", "eu", "ewe", "uk", "ur")
_AN_EXCEPTIONS_AN = ("hour", "honest", "honor", "honour", "heir")


def article_for(word: str) -> str:
    """'a' or 'an' for the following word (spelling heuristics + common exceptions)."""
    w = word.lower().lstrip("\"'“(")
    if not w:
        return "a"
    if w.startswith(_AN_EXCEPTIONS_AN):
        return "an"
    if w.startswith(_AN_EXCEPTIONS_A):
        return "a"
    if re.match(r"^[A-Z]{2,}", word.lstrip("\"'“(")):  # acronyms: "an LED", "a PLC"
        return "an" if word.lstrip("\"'“(")[0] in "AEFHILMNORSX" else "a"
    return "an" if w[0] in "aeiou" else "a"


def capitalize_first(text: str) -> str:
    for i, c in enumerate(text):
        if c.isalpha():
            return text[:i] + c.upper() + text[i + 1 :]
    return text


def lower_first(text: str) -> str:
    """Lower-case the first letter unless the first word looks like a name/acronym."""
    m = re.match(r"\s*([A-Za-z][\w'-]*)", text)
    if not m:
        return text
    word = m.group(1)
    if word == "I" or word.isupper() or any(c.isupper() for c in word[1:]):
        return text
    i = m.start(1)
    return text[:i] + word[0].lower() + text[i + 1 :]


def is_sentence_start(text: str, pos: int) -> bool:
    """True if `pos` is at the start of the sentence text (ignoring quotes/space)."""
    return text[:pos].strip(" \"'“(") == ""
