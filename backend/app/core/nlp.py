"""Process-wide singletons: spaCy pipeline, fluency LM, LanguageTool, wordfreq."""

from __future__ import annotations

from functools import lru_cache

import spacy
from spacy.language import Language
from spacy.tokens import Doc
from wordfreq import zipf_frequency

from app.config import settings
from app.core.languagetool import LanguageToolClient, get_languagetool

__all__ = ["LanguageToolClient", "get_languagetool", "get_lm", "get_nlp", "parse", "zipf"]


@lru_cache(maxsize=1)
def get_nlp() -> Language:
    return spacy.load(settings.spacy_model)


@lru_cache(maxsize=512)
def parse(text: str) -> Doc:
    """Parse text with spaCy (memoised: many modules parse the same text)."""
    return get_nlp()(text)


@lru_cache(maxsize=65536)
def zipf(word: str) -> float:
    return zipf_frequency(word.lower(), "en")


def get_lm():  # type: ignore[no-untyped-def]
    from app.humanize.ranking.fluency import get_fluency_scorer

    return get_fluency_scorer()
