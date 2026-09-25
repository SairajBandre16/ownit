"""Unit tests for P5: the 'Make it yours' generic-spot detector and /personalize/spots."""

from __future__ import annotations

import pytest

from app.personalize.generic_detector import MAX_PER_PARAGRAPH, find_spots, patterns


def kinds(text: str) -> list[str]:
    return [s.pattern for s in find_spots(text)]


# --- resource ---------------------------------------------------------------------------------


def test_lexicon_has_300_entries_and_a_prompt_per_rule():
    data = patterns()
    lists = [v for k, v in data.items() if isinstance(v, list)]
    assert sum(len(v) for v in lists) >= 300
    for rule in (
        "abstract_claim",
        "vague_source",
        "vague_benefit",
        "results_no_number",
        "vague_quantifier",
        "vague_intensifier",
        "vague_time",
        "conclusion_no_voice",
        "no_concrete_run",
    ):
        assert {"label", "prompt", "starter"} <= set(data["prompts"][rule])


# --- abstract claims --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Renewable energy plays a crucial role in modern society.",
        "Machine learning is widely used in many industries today.",
        "Robotics has many applications in manufacturing and healthcare.",
        "Blockchain technology has the potential to transform supply chains.",
        "Smart grids have paved the way for cleaner power systems.",
    ],
)
def test_abstract_claim_fires(text):
    assert kinds(text) == ["abstract_claim"]


@pytest.mark.parametrize(
    "text",
    [
        "PLCs are widely used in industry, for example in the bottling line at Tata Motors.",
        "Sensors play a crucial role in the system, such as the DHT22 we used.",
        "Robotics has many applications in manufacturing. In our lab, a KUKA arm welds 40 joints per hour.",
        "Machine learning is widely used in medicine (Rajkomar et al., 2019).",
        "Heat pumps are widely used in Norway, where 60% of homes have one.",
    ],
)
def test_abstract_claim_must_not_fire_with_example(text):
    assert "abstract_claim" not in kinds(text)


def test_abstract_claim_prompt_names_the_subject():
    spot = find_spots("Water scarcity plays a crucial role in agriculture.")[0]
    assert "water scarcity" in spot.prompt
    assert spot.quote == "plays a crucial role in"
    assert spot.starter


# --- vague sources, benefits, quantifiers, intensifiers, time ---------------------------------


@pytest.mark.parametrize(
    ("text", "pattern"),
    [
        ("Studies have shown that shading lowers the panel output.", "vague_source"),
        ("It is well known that corrosion weakens steel joints.", "vague_source"),
        ("The new layout will improve efficiency across the workshop floor.", "vague_benefit"),
        ("Automation helps reduce costs for the plant owners.", "vague_benefit"),
        ("The controller supports various sensors and output devices.", "vague_quantifier"),
        ("A wide range of materials can be printed on this machine.", "vague_quantifier"),
        ("The upgrade reduced the vibration dramatically during the trial.", "vague_intensifier"),
        ("Electric vehicles have become popular in recent years among students.", "vague_time"),
        ("Nowadays, most workshops rely on computer numerical control machines.", "vague_time"),
    ],
)
def test_phrase_rules_fire(text, pattern):
    assert pattern in kinds(text)


@pytest.mark.parametrize(
    "text",
    [
        "Studies have shown that shading lowers the panel output (Kumar, 2020).",
        "Studies have shown that shading lowers the panel output [4].",
        "The new layout will improve efficiency by 12% across the workshop floor.",
        "The controller supports 6 sensors and 2 output devices, among various options.",
        "The upgrade reduced the vibration dramatically, from 4.2 mm/s to 1.1 mm/s.",
        "Electric vehicles have become popular in recent years, with sales doubling since 2019.",
        'The manual says "a wide range of materials" can be used.',
    ],
)
def test_phrase_rules_must_not_fire_with_evidence(text):
    assert kinds(text) == []


def test_evidence_in_next_sentence_counts_for_look_ahead_rules():
    text = "The retrofit reduced losses significantly. Losses fell from 14 kW to 9 kW."
    assert "vague_intensifier" not in kinds(text)


# --- results without numbers ------------------------------------------------------------------

RESULTS = "Results\n{}\n"


@pytest.mark.parametrize(
    "sentence",
    [
        "The output voltage increased as the load was reduced.",
        "The new design performed better than the old one in every test.",
        "The efficiency of the pump remained stable during the whole run.",
        "Higher speeds produced a rougher surface on the aluminium parts.",
        "The results clearly show that the controller is the best solution.",
    ],
)
def test_results_without_numbers_fire(sentence):
    assert kinds(RESULTS.format(sentence)) == ["results_no_number"]


@pytest.mark.parametrize(
    "text",
    [
        RESULTS.format("The output voltage increased to 12.4 V as the load was reduced."),
        RESULTS.format("The efficiency stayed above 80% for the whole run."),
        RESULTS.format("The stress distribution is shown in Fig. 4 for the loaded beam."),
        "Introduction\nThe output voltage increased as the load was reduced.\n",
        RESULTS.format("Why did the output voltage increase when the load was reduced?"),
    ],
)
def test_results_rule_must_not_fire(text):
    assert "results_no_number" not in kinds(text)


# --- conclusion without the student's voice -----------------------------------------------------


def test_conclusion_without_voice_fires_on_last_sentence():
    text = (
        "Conclusion\nThe system met the design requirements for the pilot farm. "
        "Further work could extend the controller to other crops and soils.\n"
    )
    spots = find_spots(text)
    concl = [s for s in spots if s.pattern == "conclusion_no_voice"]
    assert len(concl) == 1
    assert text[concl[0].insert_at - 6 : concl[0].insert_at] == "soils."


@pytest.mark.parametrize(
    "sentence",
    [
        "We learned that calibration matters more than the sensor price.",
        "In my opinion, the relay was the weakest part of the design.",
        "The main limitation was the short test period on one farm plot.",
        "I would use a larger tank next time to avoid dry runs.",
        "The most surprising result was how quickly the soil dried out.",
    ],
)
def test_conclusion_with_voice_must_not_fire(sentence):
    text = f"Conclusion\nThe system met the design requirements for the pilot farm. {sentence}\n"
    assert "conclusion_no_voice" not in kinds(text)


def test_ie_is_not_first_person():
    text = "Conclusion\nThe controller met the target, i.e. the soil stayed moist for the season.\n"
    assert "conclusion_no_voice" in kinds(text)


# --- runs of sentences with nothing concrete --------------------------------------------------


def test_run_of_abstract_sentences_fires_once():
    text = (
        "The system is designed to be simple and effective for the user. "
        "It reduces the effort needed to maintain the plants at home. "
        "The approach is flexible and can be adapted to different needs. "
        "Overall, the design is easy to understand and to extend later."
    )
    spots = [s for s in find_spots(text) if s.pattern == "no_concrete_run"]
    assert len(spots) == 1
    assert spots[0].insert_at == len(text)


@pytest.mark.parametrize(
    "middle",
    [
        "It uses an ESP32 board to read the moisture sensor.",
        "It was tested at the Pune campus greenhouse over one week.",
        "It draws 0.5 A from the supply in normal operation.",
        "It follows the method described by Rao (2019) for small farms.",
        "It sends the readings to the MQTT broker every minute.",
    ],
)
def test_concrete_sentence_breaks_the_run(middle):
    text = (
        "The system is designed to be simple and effective for the user. "
        f"{middle} "
        "The approach is flexible and can be adapted to different needs. "
        "Overall, the design is easy to understand and to extend later."
    )
    assert "no_concrete_run" not in kinds(text)


# --- selection, offsets, exclusions -----------------------------------------------------------


def test_one_spot_per_sentence_most_specific_wins():
    # abstract claim + vague quantifier + vague time in one sentence -> only the claim
    assert kinds("In recent years, various sensors have played a crucial role in farming.") == [
        "abstract_claim"
    ]


def test_at_most_two_spots_per_paragraph():
    text = (
        "Robotics plays a vital role in industry. Studies show that it saves time. "
        "Various tools are used by the teams. The benefits have grown dramatically."
    )
    assert len(find_spots(text)) == MAX_PER_PARAGRAPH


def test_spot_offsets_point_into_the_text():
    text = "Introduction\nRobotics plays a vital role in industry. It is used on assembly lines.\n"
    for s in find_spots(text):
        assert text[s.start : s.end] == s.quote
        assert s.start < s.end <= s.insert_at <= len(text)
        assert text[s.insert_at - 1] == "."


def test_headings_and_references_are_skipped():
    text = (
        "Various Applications of Robotics\n\n"
        "References\nSmith, J. Robotics plays a crucial role in industry. Various authors, 2020.\n"
    )
    assert kinds(text) == []


def test_student_style_text_has_few_spots():
    text = (
        "We built the rig from a 12 V pump, an Arduino Uno and a 3D-printed nozzle. "
        "On the first run the pump stalled at 40% duty cycle, so I added a flyback diode. "
        "After that, it ran for 3 hours without a fault."
    )
    assert find_spots(text) == []


# --- endpoint ---------------------------------------------------------------------------------


def test_personalize_endpoint(client):
    text = "Introduction\nRobotics plays a vital role in industry. It is used on assembly lines.\n"
    r = client.post("/personalize/spots", json={"text": text})
    assert r.status_code == 200
    spots = r.json()["spots"]
    assert spots and spots[0]["pattern"] == "abstract_claim"
    for key in ("id", "start", "end", "insert_at", "label", "prompt", "starter", "quote"):
        assert key in spots[0]


def test_personalize_endpoint_word_limit(client):
    assert client.post("/personalize/spots", json={"text": "word " * 3001}).status_code == 413
