"""Loading of JSON lexicons from app/resources (cached)."""

from __future__ import annotations

from functools import cache
from typing import Any

import orjson

from app.config import RESOURCES_DIR


@cache
def load(name: str) -> Any:
    """Load `resources/<name>.json`."""
    path = RESOURCES_DIR / f"{name}.json"
    return orjson.loads(path.read_bytes())


@cache
def lesson(slug: str) -> str | None:
    path = RESOURCES_DIR / "lessons" / f"{slug}.md"
    return path.read_text(encoding="utf-8") if path.exists() else None


def lesson_slugs() -> list[str]:
    return sorted(p.stem for p in (RESOURCES_DIR / "lessons").glob("*.md"))
