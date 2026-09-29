"""Pipeline-level tests: protected-span invariant (fuzz), change offsets, endpoint."""

from __future__ import annotations

import random

import pytest

from app.humanize.pipeline import humanize

PROTECTED_BITS = [
    "$x^2 + y = 3$",
    "V = I × R",
    "25 kN",
    "3.3V",
    "±0.2 mm",
    "10^5 Pa",
    "(Smith et al., 2021)",
    "(Rao and Iyer, 2019)",
    "[4]",
    "[2–5]",
    "Fig. 3",
    "Table 2",
    "Eq. (4)",
    '"in order to reset the unit"',
    "`np.mean(x)`",
    "85%",
    "PLC",
    "MOSFET",
]

FRAMES = [
    "In today's fast-paced world, it is important to note that {a} plays a crucial role in the design.",
    "Moreover, the system has the ability to measure {a} in order to control the pump.",
    "Moreover, a large number of engineers utilize {a} due to the fact that it is cheap.",
    "The results clearly demonstrate that {a} is very important, as shown in {b}.",
    "Furthermore, the controller makes a decision based on {a} and {b}.",
    "It should be noted that the value of {a} was recorded at the present time.",
    "The prototype was assembled with {a} on a wooden base and a steel bracket, and the students "
    "then measured the output at five different wind speeds in the laboratory near {b}.",
    "In addition, the team conducted an analysis of {a}, which revealed a plethora of issues.",
]


def fuzz_text(rng: random.Random) -> tuple[str, list[str]]:
    used: list[str] = []
    sentences = []
    for _ in range(rng.randint(3, 7)):
        frame = rng.choice(FRAMES)
        a, b = rng.sample(PROTECTED_BITS, 2)
        used += [a, b] if "{b}" in frame else [a]
        sentences.append(frame.format(a=a, b=b))
    return " ".join(sentences), used


@pytest.mark.parametrize("seed", range(25))
def test_protected_spans_are_byte_identical(seed):
    rng = random.Random(seed)
    text, used = fuzz_text(rng)
    out = humanize(
        text, tone=rng.choice(["academic", "neutral", "casual"]), intensity=rng.randint(1, 5)
    )
    for bit in set(used):
        assert out.text.count(bit) == text.count(bit), (bit, text, out.text)
    for p in out.protected:
        span = text[p.start : p.end]
        assert span in out.text, (span, out.text)


def test_change_offsets_are_exact():
    text = (
        "In order to measure torque, it is important to note that we utilize a strain gauge. "
        "Moreover, the sensor has the ability to record data at 1 kHz. Moreover, the logger "
        "saves the data."
    )
    out = humanize(text, intensity=3)
    assert out.changes
    for c in out.changes:
        assert text[c.orig_start : c.orig_end] == c.original
        assert out.text[c.new_start : c.new_end] == c.replacement
        assert c.reason


def test_no_change_on_clean_text():
    text = "We fitted two sensors to the lathe. The logger saved one reading per second."
    out = humanize(text, intensity=3)
    assert out.text == text
    assert out.changes == []


def test_intensity_one_only_uses_gentle_transforms():
    text = (
        "The prototype was assembled on a wooden base with four bolts and a steel bracket, and the "
        "students then measured the output voltage at five different wind speeds in the lab. "
        "We utilize a pump in order to move water."
    )
    out = humanize(text, intensity=1)
    assert {c.transform for c in out.changes} <= {"phrase_simplify", "transition_vary", "dash_tidy"}


def test_headings_and_references_untouched():
    text = (
        "Introduction\nIt is important to note that pumps move water.\n\n"
        "References\nSmith, J. (2021). In order to pump: a study. Journal of Pumps."
    )
    out = humanize(text, intensity=5)
    assert out.text.startswith("Introduction\n")
    assert "In order to pump: a study." in out.text


def test_humanize_endpoint(client):
    body = {
        "text": "We utilize a pump in order to move water. It is important to note that it is loud.",
        "tone": "academic",
        "intensity": 3,
        "keep_terms": [],
    }
    r = client.post("/humanize", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["text"] != body["text"]
    assert 0 <= data["score_before"] <= 100 and 0 <= data["score_after"] <= 100
    for c in data["changes"]:
        assert body["text"][c["orig_start"] : c["orig_end"]] == c["original"]
        assert data["text"][c["new_start"] : c["new_end"]] == c["replacement"]


def test_keep_terms_respected(client):
    body = {
        "text": "We utilize a pump in order to move water.",
        "keep_terms": ["utilize"],
        "intensity": 3,
    }
    data = client.post("/humanize", json=body).json()
    assert "utilize" in data["text"]


def test_humanize_validation(client):
    assert client.post("/humanize", json={"text": "x", "intensity": 9}).status_code == 422
