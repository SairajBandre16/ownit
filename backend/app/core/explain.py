"""Human-readable reason/message templates from resources/explanations.json."""

from __future__ import annotations

import string
from typing import Any

from app.core.resources import load


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def explain(key: str, **values: Any) -> str:
    templates: dict[str, str] = load("explanations")
    template = templates.get(key)
    if template is None:
        raise KeyError(f"no explanation template {key!r}")
    return string.Formatter().vformat(template, (), _SafeDict(values))
