"""Short lessons (resources/lessons/*.md) linked from issues via `lesson_slug`.

A lesson file starts with "# Title" and a "> one-line summary"; the rest is Markdown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

LESSONS_DIR = Path(__file__).resolve().parent.parent / "resources" / "lessons"
SLUG_RE = re.compile(r"^[a-z0-9-]{1,60}$")
GROUPS = {
    "Clear writing": [
        "sentence-length",
        "sentence-rhythm",
        "sentence-openers",
        "concision",
        "nominalizations",
        "strong-verbs",
        "word-choice",
        "transitions",
    ],
    "Voice and tone": ["passive-voice", "hedging", "fillers", "cliches", "stock-phrases"],
    "Correctness": ["grammar", "spelling", "punctuation"],
    "Engineering reports": [
        "units",
        "abbreviations",
        "figures-and-tables",
        "tense",
        "citing-claims",
        "report-structure",
    ],
    "Owning your work": ["specific-detail", "viva-preparation"],
}


@dataclass(frozen=True)
class Lesson:
    slug: str
    title: str
    summary: str
    group: str
    markdown: str  # body without the title and summary lines


def _group_of(slug: str) -> str:
    return next((g for g, slugs in GROUPS.items() if slug in slugs), "More")


def parse_lesson(slug: str, raw: str) -> Lesson:
    lines = raw.strip().splitlines()
    title = slug.replace("-", " ").capitalize()
    summary = ""
    body_start = 0
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        body_start = 1
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1
    if body_start < len(lines) and lines[body_start].startswith("> "):
        summary = lines[body_start][2:].strip()
        body_start += 1
    return Lesson(slug, title, summary, _group_of(slug), "\n".join(lines[body_start:]).strip())


@lru_cache(maxsize=1)
def all_lessons() -> dict[str, Lesson]:
    out = {}
    for path in sorted(LESSONS_DIR.glob("*.md")):
        out[path.stem] = parse_lesson(path.stem, path.read_text(encoding="utf-8"))
    order = [s for slugs in GROUPS.values() for s in slugs]
    return dict(
        sorted(out.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else len(order))
    )


def get_lesson(slug: str) -> Lesson | None:
    if not SLUG_RE.match(slug):
        return None
    return all_lessons().get(slug)
