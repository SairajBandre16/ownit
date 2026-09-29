"""dash_tidy transform and the dash / contrast-formula analyzer flags."""

from __future__ import annotations

from app.analyze.score import run_analysis
from app.humanize.pipeline import humanize
from app.humanize.ranking.style_fit import StyleTargets, dash_hits
from app.humanize.transforms import dash_tidy
from tests.unit.test_transforms_v1 import texts

EM = chr(0x2014)
EN = chr(0x2013)


def one(text: str, **kw) -> str | None:  # type: ignore[no-untyped-def]
    out = texts(dash_tidy, text, **kw)
    return out[0] if out else None


# ------------------------------------------------------------------ fires


def test_two_clauses_become_two_sentences():
    assert one(f"The pump failed {EM} the relay had overheated.") == (
        "The pump failed. The relay had overheated."
    )


def test_short_aside_takes_commas():
    assert one(f"The sensor {EM} a cheap capacitive probe {EM} worked well.") == (
        "The sensor, a cheap capacitive probe, worked well."
    )


def test_long_aside_takes_brackets():
    aside = "a probe that we bought, tested and calibrated in the first week"
    assert one(f"The sensor {EM} {aside} {EM} worked well.") == f"The sensor ({aside}) worked well."


def test_explanation_takes_colon():
    assert one(f"The controller needs one thing {EM} a stable 5 V supply.") == (
        "The controller needs one thing: a stable 5 V supply."
    )


def test_continuation_takes_comma():
    assert one(f"Water use fell sharply {EM} especially during the hot weeks.") == (
        "Water use fell sharply, especially during the hot weeks."
    )


def test_spaced_en_dash_and_double_hyphen():
    assert one(f"The pump failed {EN} the relay had overheated.") == (
        "The pump failed. The relay had overheated."
    )
    assert one("The pump failed -- the relay had overheated.") == (
        "The pump failed. The relay had overheated."
    )


def test_capitalised_tail_keeps_its_case():
    assert (
        one(f"It worked {EM} ESP32 boards are reliable.") == "It worked. ESP32 boards are reliable."
    )


def test_never_leaves_a_fragment_after_a_full_stop():
    # a linking word, a relative clause or a comparison continues the sentence: comma
    assert one(f"Networks are cheap to deploy {EM} but they need careful planning.") == (
        "Networks are cheap to deploy, but they need careful planning."
    )
    assert one(
        f"The controller reads the sensor every second {EM} which keeps the loop stable."
    ) == ("The controller reads the sensor every second, which keeps the loop stable.")
    assert one(f"Calibration took one afternoon {EM} much less than we expected.") == (
        "Calibration took one afternoon, much less than we expected."
    )
    assert one(f"We added a soft starter {EM} a simple fix that cut the inrush current.") == (
        "We added a soft starter, a simple fix that cut the inrush current."
    )


# ------------------------------------------------------------------ must not fire


def test_ranges_and_hyphens_are_left_alone():
    assert one(f"The range was 10{EN}20 mm.") is None
    assert one("A well-known sensor was used.") is None
    assert one("The pump ran for 5 minutes.") is None


def test_dash_inside_a_quote_is_protected():
    assert one(f'The manual says "fit the probe {EM} then wait" before reading.') is None


def test_students_own_dash_habit_is_kept():
    def prep(ctx):  # type: ignore[no-untyped-def]
        ctx.profile = {"features": {"dashes_per_sentence": 0.4}}

    assert one(f"The pump failed {EM} the relay had overheated.", prepare=prep) is None
    assert dash_hits(f"a {EM} b", StyleTargets(dash_rate=0.4)) == 0
    assert dash_hits(f"a {EM} b", StyleTargets()) == 1


def test_too_many_dashes_are_left_for_the_student():
    assert one(f"A {EM} b {EM} c {EM} d {EM} e went wrong today.") is None


# ------------------------------------------------------------------ pipeline + analyzer


def test_pipeline_uses_it_at_the_gentlest_intensity():
    out = humanize(f"The pump failed {EM} the relay had overheated in the afternoon.", intensity=1)
    assert EM not in out.text
    assert {c.transform for c in out.changes} == {"dash_tidy"}
    assert all(c.reason for c in out.changes)


def test_analyzer_flags_dashes_and_contrast_formulas():
    text = f"The pump failed {EM} the relay had overheated. It is not just a cost issue, it is a safety issue."
    res = run_analysis(text)
    dash = [i for i in res.issues if i.rule == "dash"]
    assert len(dash) == 1 and text[dash[0].start : dash[0].end] == EM
    assert any(i.rule == "contrast_formula" for i in res.issues)
    assert not [
        i
        for i in run_analysis("The range was 10 to 20 mm. It is a safety issue.").issues
        if i.rule in ("dash", "contrast_formula")
    ]
