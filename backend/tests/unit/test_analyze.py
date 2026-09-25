from __future__ import annotations

import pytest

from app.analyze import clarity, rhythm, vocabulary, voice
from app.analyze.base import AnalyzerContext, band_score
from app.analyze.score import dedupe, run_analysis
from app.analyze.vocabulary import mtld
from app.core.segment import segment


def ctx(text: str) -> AnalyzerContext:
    return AnalyzerContext.build(segment(text))


def rules(result) -> list[str]:
    return [i.rule for i in result.issues]


# ------------------------------------------------------------------ bands


def test_band_score_interpolates_and_clamps():
    pts = [[0, 100], [10, 50], [20, 0]]
    assert band_score(-5, pts) == 100
    assert band_score(5, pts) == 75
    assert band_score(10, pts) == 50
    assert band_score(99, pts) == 0


# ------------------------------------------------------------------ clarity


def test_long_sentence_flagged():
    long = " ".join(["word"] * 35) + "."
    r = clarity.analyze(ctx("Short one. " + long))
    assert rules(r).count("long_sentence") == 1


def test_short_sentences_not_flagged():
    r = clarity.analyze(ctx("The motor spins. The gear turns. The load rises."))
    assert "long_sentence" not in rules(r)


def test_wordy_phrase_with_suggestion():
    r = clarity.analyze(ctx("We used a pump in order to move the water."))
    (iss,) = [i for i in r.issues if i.rule == "wordy_phrase"]
    assert iss.suggestion == "to"


def test_nominalization_light_verb():
    r = clarity.analyze(ctx("The team made a decision about the design."))
    iss = [i for i in r.issues if i.rule in ("nominalization", "wordy_phrase")]
    assert iss and iss[0].suggestion == "decided"


def test_wordy_not_flagged_inside_quote():
    r = clarity.analyze(ctx('The manual says "in order to reset, hold the button" clearly.'))
    assert "wordy_phrase" not in rules(r)


def test_grade_excess_zero_for_simple_text():
    r = clarity.analyze(ctx("The cat sat. The dog ran. It was fun."))
    assert r.metrics["grade_excess"] == 0


# ------------------------------------------------------------------ rhythm


def test_monotone_run_detected():
    text = (
        "The motor turns the shaft at high speed. The sensor reads the value every second. "
        "The board sends the data to the laptop. The laptop saves the data in a file."
    )
    r = rhythm.analyze(ctx(text))
    assert "monotone_run" in rules(r)


def test_varied_lengths_no_run():
    text = (
        "It failed. After three weeks of careful testing in the lab under varied loads, "
        "the bearing finally cracked near the inner race. Why? Heat."
    )
    r = rhythm.analyze(ctx(text))
    assert "monotone_run" not in rules(r)
    assert r.metrics["sentence_length_sd"] > 5


def test_repeated_opener():
    text = "The pump starts. The valve opens slowly now. The tank fills up. Water flows."
    r = rhythm.analyze(ctx(text))
    assert "repeated_opener" in rules(r)


def test_opener_entropy_higher_when_varied():
    same = rhythm.analyze(ctx("The a runs. The b runs. The c runs. The d runs."))
    varied = rhythm.analyze(ctx("The a runs. Then b runs. After that, c runs. Finally d runs."))
    assert varied.metrics["opener_entropy"] > same.metrics["opener_entropy"]


def test_single_sentence_rhythm_is_neutral():
    r = rhythm.analyze(ctx("Only one sentence here."))
    assert r.issues == []


# ------------------------------------------------------------------ vocabulary


def test_mtld_diverse_beats_repetitive():
    diverse = (
        "the quick brown fox jumps over a lazy dog while seven small birds sing loudly".split()
    )
    repetitive = ("the dog and the dog and the dog and the dog " * 3).split()
    assert mtld(diverse) > mtld(repetitive)
    assert mtld(["a", "b"]) == 0.0


def test_ai_style_phrase_flagged():
    r = vocabulary.analyze(ctx("Sensors play a crucial role in modern factories."))
    iss = [i for i in r.issues if i.rule == "ai_style_phrase"]
    assert iss and iss[0].suggestion == "are central to"


def test_cliche_flagged():
    r = vocabulary.analyze(ctx("At the end of the day, the design worked."))
    assert "cliche" in rules(r) or "ai_style_phrase" in rules(r)


def test_repeated_word_within_two_sentences():
    r = vocabulary.analyze(ctx("The motor stopped suddenly. Then the fan stopped suddenly too."))
    assert "repeated_word" in rules(r)


def test_repetition_far_apart_not_flagged():
    text = (
        "The bracket bends. The motor hums. The wire is copper. "
        "Current flows. We reinforced the bracket."
    )
    r = vocabulary.analyze(ctx(text))
    assert "repeated_word" not in rules(r)


def test_clean_text_has_no_stock_phrases():
    r = vocabulary.analyze(ctx("We measured the voltage across the resistor."))
    assert "ai_style_phrase" not in rules(r)


# ------------------------------------------------------------------ voice


def test_passive_detected_outside_methodology():
    r = voice.analyze(ctx("The data was processed by the controller."))
    (iss,) = [i for i in r.issues if i.rule == "passive"]
    assert "controller" in iss.message


def test_passive_exempt_in_methodology():
    r = voice.analyze(ctx("Methodology\nThe sample was heated to 200 °C."))
    assert "passive" not in rules(r)


def test_active_voice_not_flagged():
    r = voice.analyze(ctx("The controller processed the data."))
    assert "passive" not in rules(r)


def test_stacked_hedge_is_warning():
    r = voice.analyze(ctx("The error might possibly come from noise."))
    assert any(i.rule == "stacked_hedge" and i.severity == "warn" for i in r.issues)


def test_filler_flagged_with_suggestion():
    r = voice.analyze(ctx("The result is very important for us."))
    assert any(i.rule == "filler" for i in r.issues)


def test_weak_verb_suggestion():
    r = voice.analyze(ctx("Temperature has an effect on resistance."))
    iss = [i for i in r.issues if i.rule == "weak_verb"]
    assert iss and iss[0].suggestion == "affects"


def test_expletive_there_is_that():
    r = voice.analyze(ctx("There are many sensors that measure heat."))
    assert "expletive" in rules(r)


# ------------------------------------------------------------------ scoring


def test_dedupe_prefers_specific_rule():
    from app.analyze.base import make_issue

    a = make_issue(
        start=0, end=5, category="clarity", rule="wordy_phrase", severity="warn", message=""
    )
    b = make_issue(
        start=0, end=5, category="vocabulary", rule="ai_style_phrase", severity="warn", message=""
    )
    assert [i.rule for i in dedupe([a, b])] == ["ai_style_phrase"]


def test_run_analysis_scores_in_range():
    res = run_analysis("The pump moves water. It uses a small motor that runs at 12 V.")
    assert 0 <= res.score <= 100
    for v in res.subscores.values():
        assert v is None or 0 <= v <= 100


def test_ai_draft_scores_lower_than_clean_text():
    ai = (
        "In today's fast-paced world, it is important to note that sensors play a crucial role "
        "in the realm of manufacturing. Moreover, they seamlessly integrate a myriad of data. "
        "Furthermore, they pave the way for a plethora of innovations."
    )
    clean = (
        "Factories use sensors to track machines. A vibration sensor on a lathe can warn of a "
        "worn bearing days early. We fitted two and logged data for a week."
    )
    assert run_analysis(ai).score < run_analysis(clean).score


@pytest.mark.languagetool
def test_correctness_flags_grammar():
    res = run_analysis("The results clearly shows that the the motor overheat.")
    assert any(i.category == "correctness" for i in res.issues)


def test_analyze_endpoint(client):
    r = client.post("/analyze", json={"text": "We utilize sensors in order to monitor heat."})
    assert r.status_code == 200
    body = r.json()
    assert set(body["subscores"]) == {"clarity", "rhythm", "vocabulary", "voice", "correctness"}
    assert body["stats"]["words"] == 8
    text = "We utilize sensors in order to monitor heat."
    for iss in body["issues"]:
        assert 0 <= iss["start"] < iss["end"] <= len(text)


def test_analyze_word_limit(client):
    r = client.post("/analyze", json={"text": "word " * 3001})
    assert r.status_code == 413
