"""Unit tests for P3: structural transforms, voice fingerprint, document pass."""

from __future__ import annotations

import pytest

from app.core.nlp import parse
from app.core.protect import detect_protected
from app.core.segment import segment
from app.core.spans import SpanIndex
from app.humanize.docpass import _merge_text
from app.humanize.pipeline import humanize
from app.humanize.transforms import clause_front, contractions, opener_vary, passive_to_active, voice_fit
from app.humanize.transforms.passive_to_active import rewrite
from app.humanize.types import HumanizeContext
from app.style.delta import compare, voice_match
from app.style.fingerprint import fingerprint, text_features
from app.style.objective import VoiceObjective, opener_class


def ctx_for(text: str, tone: str = "academic", profile=None) -> HumanizeContext:
    seg = segment(text)
    idx = SpanIndex((p.start, p.end) for p in detect_protected(text))
    return HumanizeContext(seg=seg, protected=idx, tone=tone, intensity=5, profile=profile)


def texts(module, text: str, sentence: int = 0, tone: str = "academic", profile=None, prepare=None) -> list[str]:
    ctx = ctx_for(text, tone, profile)
    if prepare:
        prepare(ctx)
    view = ctx.view(ctx.seg.sentences[sentence])
    return [c.text for c in module.apply(view, ctx)]


# ------------------------------------------------------------------ passive_to_active


@pytest.mark.parametrize(
    ("passive", "active"),
    [
        ("The data was processed by the controller in real time.", "The controller processed the data in real time."),
        ("In 2020, the bridge was inspected by two engineers.", "In 2020, two engineers inspected the bridge."),
        ("The samples are tested by the lab every week.", "The lab tests the samples every week."),
        ("The motor has been replaced by the technicians.", "The technicians have replaced the motor."),
        ("The results were analysed by us using MATLAB.", "We analysed the results using MATLAB."),
        ("The report will be reviewed by the supervisor.", "The supervisor will review the report."),
        ("The circuit is being tested by the students.", "The students are testing the circuit."),
    ],
)
def test_passive_to_active_tenses(passive, active):
    assert rewrite(parse(passive)[:]) == active


@pytest.mark.parametrize(
    "sentence",
    [
        "The design was approved.",  # no agent
        "The pump was not repaired by the team.",  # negation
        "The valve that leaked was replaced by the plumber.",  # relative clause in subject
        "Was the sample heated by the furnace?",  # question
        "The team repaired the pump.",  # already active
    ],
)
def test_passive_to_active_does_not_fire(sentence):
    assert rewrite(parse(sentence)[:]) is None


def test_passive_to_active_skips_methodology():
    text = "Methodology\nThe samples were weighed by the technician before drying."
    ctx = ctx_for(text)
    body = [s for s in ctx.seg.sentences if s.section == "methodology"][0]
    assert passive_to_active.apply(ctx.view(body), ctx) == []


# ------------------------------------------------------------------ clause_front / opener_vary


def test_clause_front_both_directions():
    assert texts(clause_front, "The pump stopped because the fuse blew.") == ["Because the fuse blew, the pump stopped."]
    assert texts(clause_front, "If the voltage drops, the relay opens the circuit.") == [
        "The relay opens the circuit if the voltage drops."
    ]


def test_clause_front_ignores_other_clauses():
    assert texts(clause_front, "The pump that we bought stopped working last week.") == []
    assert texts(clause_front, "The pump stopped.") == []


def test_opener_vary_fires_on_repeated_openers():
    text = "The sample was heated in the furnace for two hours."

    def prep(ctx):
        ctx.chosen.extend(["The tube was cleaned.", "The oven was set to 200 °C.", "The scale was zeroed."])

    out = texts(opener_vary, text, prepare=prep)
    assert "For two hours, the sample was heated in the furnace." in out


def test_opener_vary_quiet_without_repetition():
    def prep(ctx):
        ctx.chosen.extend(["We cleaned the tube.", "After that, the oven heated up.", "It worked."])

    assert texts(opener_vary, "The sample was heated in the furnace for two hours.", prepare=prep) == []


def test_opener_class():
    assert opener_class("The pump runs.") == "DET"
    assert opener_class("We measured it.") == "PRON"
    assert opener_class("In the lab, we tested it.") == "ADP"
    assert opener_class("Because it failed, we stopped.") == "SCONJ"
    assert opener_class("Motors spin.") == "NOUN"


# ------------------------------------------------------------------ contractions


def test_contractions_casual():
    assert texts(contractions, "We do not know why it is noisy.", tone="casual") == ["We don't know why it's noisy."]


def test_contractions_expanded_in_academic():
    assert texts(contractions, "We don't know why it's noisy.", tone="academic") == ["We do not know why it is noisy."]


def test_contractions_neutral_without_profile_left_alone():
    assert texts(contractions, "We do not know.", tone="neutral") == []


def test_contractions_keep_clarifying_that_is():
    assert texts(contractions, "The load, that is, the weight, was small.", tone="casual") == []


def test_contractions_follow_profile_in_neutral_tone():
    profile = {"features": {"contractions_per_sentence": 0.8}, "function_word_freqs": {}}
    assert texts(contractions, "We do not know.", tone="neutral", profile=profile) == ["We don't know."]


# ------------------------------------------------------------------ voice_fit


def test_voice_fit_uses_students_favourite_transition():
    profile = {"features": {}, "function_word_freqs": {}, "_favourite_transitions": ["also"]}
    out = texts(voice_fit, "Moreover, the pump is quiet.", profile=profile)
    assert out == ["Also, the pump is quiet."]


def test_voice_fit_needs_profile():
    assert texts(voice_fit, "Moreover, the pump is quiet.") == []


def test_voice_fit_keeps_favourite():
    profile = {"features": {}, "function_word_freqs": {}, "_favourite_transitions": ["moreover"]}
    assert texts(voice_fit, "Moreover, the pump is quiet.", profile=profile) == []


# ------------------------------------------------------------------ merge_short


def test_merge_text_pronoun_back_reference():
    assert _merge_text("The pump is small.", "It fits in a box.") == ("The pump is small, and it fits in a box.", ", and")


def test_merge_text_however():
    assert _merge_text("The pump is cheap.", "However, it is loud.")[0] == "The pump is cheap; however, it is loud."


def test_merge_text_unrelated_not_merged():
    assert _merge_text("The pump is small.", "Water boils at 100 °C.") is None


def test_merge_in_pipeline_at_high_intensity():
    out = humanize("The pump is small. It fits in a box. We tested it for a week in the lab.", intensity=5)
    assert "small, and it fits in a box." in out.text
    for c in out.changes:
        assert out.text[c.new_start : c.new_end] == c.replacement


def test_no_merge_at_low_intensity():
    out = humanize("The pump is small. It fits in a box.", intensity=2)
    assert "It fits in a box." in out.text


# ------------------------------------------------------------------ voice fingerprint

STUDENT = [
    "For our mini project we built a line follower robot using two IR sensors and an Arduino Uno. "
    "The first version kept losing the line on sharp turns, so we lowered the sensors by about 5 mm. "
    "After that it completed the track in 42 seconds.",
    "We tested three mild steel samples on the UTM. The average ultimate load was 48.6 kN and the "
    "samples necked clearly before breaking. One sample broke close to the grip, so its result is "
    "probably lower than it should be. I think we should repeat that test.",
    "The main problem with our solar charger was heat. On a sunny afternoon the regulator got so hot "
    "that it shut down after twenty minutes. We added a small heat sink and the charger then ran for "
    "over two hours. I was surprised how much a cheap heat sink helped. We also moved the board into "
    "the shade, which helped a bit more. Next time we will add a temperature sensor so we can log it.",
    "I chose a bridge rectifier because it only needs one secondary winding. The ripple was still "
    "high, so I added a big capacitor. That brought the ripple down to about 0.3 V. We measured it "
    "with the oscilloscope in the lab and it looked clean. I think a bigger capacitor would help but "
    "it would take up too much space on our board.",
]
AI = (
    "In today's fast-paced world, renewable energy plays a crucial role in addressing climate change. "
    "It is important to note that solar panels have the ability to convert sunlight into electricity. "
    "Moreover, advancements in photovoltaic technology have paved the way for a plethora of innovative "
    "applications. Furthermore, the cost of solar modules has decreased significantly."
)


def test_fingerprint_features():
    p = fingerprint(STUDENT)
    assert p.sample_word_count > 150
    f = p.features
    assert 8 < f["sentence_length_mean"] < 25
    assert f["first_person_per_1000"] > 20
    assert set(p.function_word_freqs) >= {"the", "and", "we", "i"}


def test_voice_match_prefers_own_writing():
    p = fingerprint(STUDENT[:3])
    own = voice_match(STUDENT[3], p)
    ai = voice_match(AI, p)
    assert own > ai
    assert 0 <= ai <= 100 and 0 <= own <= 100


def test_compare_differences_are_plain_language():
    p = fingerprint(STUDENT)
    _, diffs = compare(AI, p)
    assert diffs
    assert all(d.message.endswith(".") for d in diffs[:3])


def test_text_features_ignore_digit_colons():
    f, _, _ = text_features("We used a 20:1 gearbox. It worked well.")
    assert f["colons_per_sentence"] == 0


def test_voice_objective_rewards_moving_towards_profile():
    p = fingerprint(STUDENT).model_dump()
    sents = [
        "Moreover, the proposed system possesses the capability to ascertain anomalies efficiently.",
        "We fitted two sensors to the board and ran the test for a week in the lab.",
    ]
    obj = VoiceObjective(p, sents)
    plain = obj.gain(0, "We found that our system spots the faults when we add them to the board.")
    formal = obj.gain(0, "Furthermore, the apparatus possesses the capability to ascertain anomalies efficiently.")
    assert plain > formal


def test_style_endpoints(client):
    r = client.post("/style/fingerprint", json={"samples": [" ".join(STUDENT), " ".join(STUDENT)]})
    assert r.status_code == 200
    profile = r.json()
    r2 = client.post("/style/compare", json={"text": AI, "profile": profile})
    assert r2.status_code == 200
    body = r2.json()
    assert 0 <= body["voice_match"] <= 100
    assert len(body["differences"]) <= 3


def test_fingerprint_needs_300_words(client):
    r = client.post("/style/fingerprint", json={"samples": ["Too short to be a real sample."]})
    assert r.status_code == 422


def test_humanize_with_profile_reports_voice_match(client):
    profile = client.post("/style/fingerprint", json={"samples": [" ".join(STUDENT)] * 2}).json()
    r = client.post("/humanize", json={"text": AI, "intensity": 4, "style_profile": profile})
    body = r.json()
    assert body["voice_match"] is not None and body["voice_match_before"] is not None
