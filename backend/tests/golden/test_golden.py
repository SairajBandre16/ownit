"""Golden tests: input -> expected properties of the humanized output (tests/golden/*.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.humanize.pipeline import humanize

CASES = json.loads((Path(__file__).parent / "golden_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_golden(case):
    p = case["params"]
    out = humanize(
        case["input"],
        tone=p.get("tone", "academic"),
        intensity=p.get("intensity", 3),
        keep_terms=tuple(p.get("keep_terms", [])),
    )
    for s in case.get("must_contain", []):
        assert s in out.text, f"missing {s!r} in {out.text!r}"
    for s in case.get("must_not_contain", []):
        assert s not in out.text, f"unexpected {s!r} in {out.text!r}"
    for s in case.get("must_not_change", []):
        assert out.text.count(s) == case["input"].count(s)
    assert len(out.changes) <= case["max_changes"], [c.original for c in out.changes]
