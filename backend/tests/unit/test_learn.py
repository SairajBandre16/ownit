"""Lessons: every lesson_slug an issue can point to has a lesson, and the API serves them."""

from __future__ import annotations

import re
from pathlib import Path

from app.learn.lessons import GROUPS, all_lessons, get_lesson, parse_lesson

APP = Path(__file__).resolve().parents[2] / "app"


def used_slugs() -> set[str]:
    found: set[str] = set()
    for path in APP.rglob("*.py"):
        src = path.read_text(encoding="utf-8")
        found |= set(re.findall(r'lesson_slug="([a-z-]+)"', src))
        found |= set(re.findall(r'^LESSON = "([a-z-]+)"', src, flags=re.MULTILINE))
        for m in re.findall(r"^LESSON = \{([^}]*)\}", src, flags=re.MULTILINE):
            found |= set(re.findall(r':\s*"([a-z-]+)"', m))
    return found


def test_every_issue_slug_has_a_lesson():
    slugs = used_slugs()
    assert len(slugs) >= 15
    assert slugs <= set(all_lessons()), slugs - set(all_lessons())


def test_every_lesson_is_grouped_and_well_formed():
    grouped = {s for g in GROUPS.values() for s in g}
    for slug, lesson in all_lessons().items():
        assert slug in grouped, slug
        assert lesson.title and lesson.summary and len(lesson.markdown.split()) > 60
        assert not lesson.markdown.startswith("# ")


def test_parse_lesson_and_bad_slugs():
    x = parse_lesson("demo", "# Demo title\n> Short.\n\n## Part\nText.")
    assert (x.title, x.summary, x.markdown) == ("Demo title", "Short.", "## Part\nText.")
    assert get_lesson("../secrets") is None and get_lesson("nope") is None


def test_lesson_endpoints(client):
    index = client.get("/lessons").json()
    assert index[0]["slug"] == "sentence-length" and {"slug", "title", "summary", "group"} <= set(
        index[0]
    )
    one = client.get("/lessons/units").json()
    assert one["title"].startswith("Units") and "12 V" in one["markdown"]
    assert client.get("/lessons/missing").status_code == 404
