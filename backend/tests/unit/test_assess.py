"""Unit tests for P6: key sentences, cloze/MCQ/TF/viva generation, grading, teach-back and
the /assess endpoints."""

from __future__ import annotations

import pytest

from app.assess.cloze import make_cloze
from app.assess.concepts import aliases_for, doc_keyphrases
from app.assess.grade import cloze_correct, copied_share, grade_open, levenshtein, similarity
from app.assess.keysent import find_definition, key_sentences, opener_length
from app.assess.mcq import _is_abbr, distractors, make_mcq
from app.assess.service import generate, grade_all
from app.assess.teachback import teachback
from app.assess.true_false import flip, make_false, negate, swap_numbers
from app.assess.types import Question
from app.assess.viva import (
    SESSION_LENGTH,
    Turn,
    build_bank,
    causal_q,
    choice_q,
    comparison_q,
    effect_q,
    method_q,
    next_question,
    result_value_q,
    why_question,
)
from app.core.nlp import parse
from app.core.segment import segment

REPORT = """Design of a Smart Irrigation Controller

Introduction
A programmable logic controller (PLC) is an industrial computer that controls machines in real time. Water scarcity reduces crop yield in dry regions. The soil moisture sensor measures the volumetric water content of the soil. A relay module switches the pump when the soil is dry.

Methodology
The controller was built around an ESP32 board. A capacitive soil moisture sensor was used because it does not corrode in wet soil. The pump was switched by a relay module rated at 10 A. The data was sent to a cloud dashboard every 10 minutes.

Results
The water use fell from 120 L to 84 L per week compared with manual watering. The moisture level stayed within the target band for most of the test period. Higher temperatures increased the evaporation rate in the afternoon.

Conclusion
The smart irrigation controller reduced water use by 30% on the test plot.
"""


@pytest.fixture(scope="module")
def seg():  # type: ignore[no-untyped-def]
    return segment(REPORT)


def sent_of(seg, fragment: str):  # type: ignore[no-untyped-def]
    return next(s for s in seg.sentences if fragment in s.text)


def ks_of(seg, fragment: str):  # type: ignore[no-untyped-def]
    return next(k for k in key_sentences(seg) if fragment in k.sent.text)


# --- key sentences ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "term"),
    [
        (
            "A programmable logic controller (PLC) is an industrial computer that runs code.",
            "programmable logic controller",
        ),
        ("An actuator is a device that converts energy into motion.", "actuator"),
        ("Hysteresis refers to the lag between input and output of a system.", "Hysteresis"),
        (
            "The duty cycle is defined as the fraction of one period in which a signal is active.",
            "duty cycle",
        ),
        ("Thermocouples are sensors that measure temperature using two metals.", None),
    ],
)
def test_find_definition(text, term):
    d = find_definition(segment(text).sentences[0])
    if term is None:
        assert d is None or d.term == "Thermocouples"
    else:
        assert d is not None and d.term == term
        assert text[d.start : d.end] == term


@pytest.mark.parametrize(
    "text",
    [
        "The pump is red and small.",
        "It is a good idea to test the sensor first.",
        "The controller is the best solution for small farms.",
        "What is a relay and how does it work in this circuit?",
        "This is an important step in the whole process.",
    ],
)
def test_find_definition_must_not_fire(text):
    assert find_definition(segment(text).sentences[0]) is None


def test_opener_length_strips_stock_openers():
    for text, rest in [
        (
            "Moreover, it is important to note that the pump failed twice in the first week.",
            "the pump failed",
        ),
        ("It can be seen that the rate was higher in the first two hours.", "the rate was"),
        (
            "In conclusion, it is evident that the controller works on small farms.",
            "the controller",
        ),
    ]:
        assert text[opener_length(text) :].startswith(rest)
    assert opener_length("The pump failed twice during the second week.") == 0
    assert opener_length("Moreover, it failed.") == 0  # too little left


def test_key_sentences_skip_titles_headings_and_fragments(seg):
    texts = [k.sent.text for k in key_sentences(seg)]
    assert not any("Design of a Smart" in t for t in texts)
    assert "Methodology" not in texts
    assert all(t.rstrip()[-1] in ".!?" for t in texts)


def test_confusing_paragraphs_are_flagged(seg):
    para = "The controller was built around an ESP32 board. A capacitive soil moisture sensor"
    keys = key_sentences(seg, [REPORT[REPORT.index(para) : REPORT.index("every 10 minutes.") + 17]])
    assert any(k.confusing for k in keys)
    assert not any(k.confusing and "Water scarcity" in k.sent.text for k in keys)


# --- cloze --------------------------------------------------------------------------------------


def test_cloze_blanks_a_keyphrase_once(seg):
    ks = ks_of(seg, "The soil moisture sensor measures")
    q = make_cloze(ks, doc_keyphrases(seg), seg, aliases_for(seg), "q1", set())
    assert q is not None and q.type == "cloze"
    assert q.prompt.count("_____") == 1
    assert q.answer_key.lower() not in q.prompt.lower()
    assert q.explanation.startswith("The soil moisture sensor")


def test_cloze_blanks_abbreviation_with_its_expansion(seg):
    ks = ks_of(seg, "programmable logic controller")
    q = make_cloze(ks, doc_keyphrases(seg), seg, aliases_for(seg), "q1", set())
    assert q is not None
    assert "PLC" not in q.prompt and "programmable logic controller" not in q.prompt.lower()


def test_cloze_skips_used_terms(seg):
    ks = ks_of(seg, "The soil moisture sensor measures")
    first = make_cloze(ks, doc_keyphrases(seg), seg, aliases_for(seg), "q1", set())
    assert first is not None
    again = make_cloze(
        ks, doc_keyphrases(seg), seg, aliases_for(seg), "q2", {first.answer_key.lower()}
    )
    assert again is None or again.answer_key != first.answer_key


@pytest.mark.parametrize(
    ("answer", "key", "accepted", "ok"),
    [
        ("capacitive soil moisture sensors", "capacitive soil moisture sensor", [], True),
        ("capacitve soil moisture sensor", "capacitive soil moisture sensor", [], True),
        ("The relay module", "relay module", [], True),
        ("PLC", "programmable logic controller", ["PLC"], True),
        ("moisture sensor", "capacitive soil moisture sensor", [], False),
        ("bolt", "bold", [], False),  # typos only forgiven on words longer than 5 letters
        ("", "relay", [], False),
    ],
)
def test_cloze_grading(answer, key, accepted, ok):
    assert cloze_correct(answer, key, accepted) is ok


def test_levenshtein():
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("same", "same") == 0


# --- MCQ ----------------------------------------------------------------------------------------


def test_mcq_has_three_distractors_not_in_the_sentence(seg):
    keys = sorted(key_sentences(seg), key=lambda k: -k.score)
    q = next(
        (
            q
            for k in keys
            if (q := make_mcq(k, doc_keyphrases(seg), seg, aliases_for(seg), "m", set()))
        ),
        None,
    )
    assert q is not None and q.options is not None
    assert len(q.options) == 4 and q.answer_key in q.options
    sentence = q.explanation.lower()
    for o in q.options:
        if o != q.answer_key:
            assert o.lower() not in sentence


def test_distractors_match_the_kind_of_answer(seg):
    pool = ["ESP32", "IoT", "relay module", "cloud dashboard", "pump"]
    out = distractors("PLC", "The PLC reads the sensor.", [*pool, "ADC", "PWM"], seg, {})
    assert len(out) == 3 and all(_is_abbr(o) for o in out)
    nps = distractors("relay module", "A relay module switches it.", pool, seg, {})
    assert "ESP32" not in nps and "IoT" not in nps


def test_no_mcq_without_enough_distractors():
    s = segment("The zorblat spins inside the quenx of the small test motor during each run.")
    ks = key_sentences(s)[0]
    assert distractors("zorblat", ks.text, ["quenx"], s, {}) == []  # in the sentence, no WordNet
    assert make_mcq(ks, ["zorblat"], s, {}, "m", set()) is None


# --- true / false ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "The output voltage increased with the load.",
            "The output voltage decreased with the load.",
        ),
        ("Higher speeds gave a rougher surface.", "Lower speeds gave a rougher surface."),
        ("The error was less than expected.", "The error was more than expected."),
    ],
)
def test_flip(text, expected):
    assert flip(text) == expected


def test_swap_numbers():
    assert (
        swap_numbers("The water use fell from 120 L to 84 L per week.")
        == "The water use fell from 84 L to 120 L per week."
    )
    assert swap_numbers("It ran for 10 minutes.") is None
    assert swap_numbers("The ESP32 has 2 cores and 2 radios.") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The pump was switched by a relay.", "The pump was not switched by a relay."),
        (
            "The sensor measures the water content.",
            "The sensor does not measure the water content.",
        ),
        ("The controller reduced water use.", "The controller did not reduce water use."),
        ("The relay can switch 10 A.", "The relay cannot switch 10 A."),
        ("The moisture level is stable.", "The moisture level is not stable."),
    ],
)
def test_negate(text, expected):
    assert negate(text) == expected


def test_negate_must_not_double_negate():
    assert negate("The sensor does not corrode in wet soil.") is None
    assert negate("The pump never ran dry.") is None


def test_make_false_never_returns_the_original():
    text = "The data was sent to a cloud dashboard every 10 minutes."
    res = make_false(text, ["cloud dashboard"])
    assert res is not None and res[0] != text


# --- viva ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("clause", "question"),
    [
        ("the pump stopped", "Why did the pump stop?"),
        ("the specimen was loaded slowly", "Why was the specimen loaded slowly?"),
        ("the overshoot is small", "Why is the overshoot small?"),
        ("we chose a relay module", "Why did you choose a relay module?"),
        (
            "the sensor measures the water content every minute",
            "Why does the sensor measure the water content every minute?",
        ),
    ],
)
def test_why_question(clause, question):
    assert why_question(clause) == question


@pytest.mark.parametrize(
    "clause",
    [
        "it stopped",  # vague pronoun subject
        "this discrepancy may possibly be",  # hedged and empty
        "the pump did not stop",  # negated
        "in the morning the pump stopped",  # fronted phrase
        "stopped",
        "our lower value is likely",  # only a hedge is left once "due to …" is removed
        "the difference is probably",
    ],
)
def test_why_question_must_not_fire(clause):
    assert why_question(clause) is None


def test_template_generators():
    assert (
        effect_q(parse("Higher temperatures increase the evaporation rate.")).prompt
        == ("How do higher temperatures affect the evaporation rate?")
        or "higher temperatures"
        in effect_q(parse("Higher temperatures increase the evaporation rate.")).prompt
    )
    assert (
        method_q(parse("The specimen was loaded at 2 mm/min.")).prompt
        == "How did you load the specimen?"
    )
    assert (
        "a capacitive sensor"
        in choice_q(parse("A capacitive sensor was used to measure moisture.")).prompt
    )
    causal = causal_q(parse("The pump stopped because the fuse blew."))
    assert causal is not None and causal.prompt == "Why did the pump stop?"
    rv = result_value_q(parse("The efficiency reached 91.4% at full load."), "results")
    assert rv is not None and "91.4%" in rv.prompt
    cmp_ = comparison_q(parse("The PID controller settled faster than the on-off controller."))
    assert cmp_ is not None and "on-off controller" in cmp_.prompt


def test_template_generators_must_not_fire():
    assert effect_q(parse("The pump is blue.")) is None
    assert effect_q(parse("Cloud computing has changed the way we store data.")) is None
    assert method_q(parse("The results were good.")) is None
    assert choice_q(parse("It was used.")) is None
    assert causal_q(parse("The pump stopped at noon.")) is None
    assert (
        result_value_q(parse("The efficiency reached 91.4% at full load."), "introduction") is None
    )
    assert comparison_q(parse("The efficiency was more than 90%.")) is None


def test_bank_questions_are_well_formed(seg):
    bank = build_bank(seg)
    assert len(bank) >= 6
    assert {q.level for q in bank} >= {1, 2, 3}
    for q in bank:
        assert q.prompt[0].isupper() and q.prompt.rstrip()[-1] in "?."
        assert "_" not in q.prompt and "  " not in q.prompt
        assert REPORT[q.source_start : q.source_end].strip()


def test_viva_ladder_moves_up_down_and_stops(seg):
    first = next_question(seg, [])
    assert first is not None and first.level == 1
    up = next_question(seg, [Turn(first.prompt, "good", 90, first.id)])
    assert up is not None and up.level is not None and up.level >= 2 and up.prompt != first.prompt
    down = next_question(
        seg,
        [Turn(first.prompt, "x", 90, first.id), Turn(up.prompt, "no", 10, up.id, ["relay module"])],
    )
    assert down is not None and down.level == 1
    history = [Turn(f"q{i}", "a", 50) for i in range(SESSION_LENGTH)]
    assert next_question(seg, history) is None


def test_viva_never_repeats_a_question(seg):
    history: list[Turn] = []
    prompts = []
    for _ in range(8):
        q = next_question(seg, history)
        if q is None:
            break
        prompts.append(q.prompt)
        history.append(Turn(q.prompt, "answer", 55, q.id))
    assert len(prompts) == len(set(prompts))


# --- grading ------------------------------------------------------------------------------------


def test_grade_open_rewards_coverage_and_own_words():
    src = "The pump was switched by a relay module rated at 10 A."
    good = grade_open(
        "A relay module rated for 10 A turned the pump on and off.", ["relay module", "pump"], src
    )
    vague = grade_open("It was controlled somehow by the circuit.", ["relay module", "pump"], src)
    empty = grade_open("no", ["relay module", "pump"], src)
    copied = grade_open(src, ["relay module", "pump"], src)
    assert good.score >= 70 and good.missed == []
    assert vague.score < 40 and "relay module" in vague.feedback
    assert empty.score == 0
    assert copied.copied and copied.score <= 50 and "own words" in copied.feedback


def test_concepts_match_synonyms_and_abbreviations():
    src = "The PLC controls the conveyor motor."
    g = grade_open(
        "The programmable logic controller drives the belt motor.",
        ["PLC", "motor"],
        src,
        {"plc": "programmable logic controller"},
    )
    assert g.covered == ["PLC", "motor"]


def test_similarity_bounds():
    assert similarity("", "The pump runs.") == 0.0
    assert similarity("The pump pushes water.", "The pump pushes water.") == 1.0
    assert similarity("I like football and pizza.", "The relay switches the pump.") < 0.3
    assert (
        copied_share("the pump was switched by a relay", "The pump was switched by a relay module.")
        == 1.0
    )


def test_grade_all_totals_closed_questions():
    qs = [
        Question("a", "cloze", "The _____ runs.", "pump", 0, 10, ["pump"]),
        Question(
            "b",
            "mcq",
            "The _____ runs.",
            "pump",
            0,
            10,
            ["pump"],
            options=["pump", "fan", "motor", "valve"],
        ),
        Question("c", "tf", "The pump runs.", "true", 0, 10),
        Question(
            "d", "tf", "The pump stops.", "false", 0, 10, kind="flip", explanation="The pump runs."
        ),
    ]
    results, total = grade_all(qs, {"a": "pumps", "b": "fan", "c": "true", "d": "true"})
    assert [r.correct for r in results] == [True, False, True, False]
    assert total == 50.0
    assert "The text says" in results[3].feedback


# --- teach-back ---------------------------------------------------------------------------------


def test_teachback_scores_a_real_explanation_above_a_vague_one(seg):
    good = teachback(
        seg,
        "The smart irrigation controller uses an ESP32 and a capacitive soil moisture sensor to measure the "
        "volumetric water content. A relay module switches the pump when the soil is dry, and the data goes "
        "to a cloud dashboard. Water use fell compared with manual watering, which matters because water "
        "scarcity reduces crop yield.",
    )
    vague = teachback(seg, "The project was about farming and it worked well in the end.")
    assert good.grade.coverage >= 0.6 and good.grade.score > vague.grade.score + 30
    assert vague.grade.missed and all(c in vague.sources for c in vague.grade.missed if c in REPORT)


# --- generation + endpoints -----------------------------------------------------------------------


def test_generate_mix_and_confusing_priority(seg):
    qs = generate(seg)
    quiz = [q for q in qs if q.type != "viva"]
    assert len(quiz) >= 8
    assert {q.type for q in quiz} == {"cloze", "mcq", "tf"}
    tf = [q for q in quiz if q.type == "tf"]
    assert {q.answer_key for q in tf} == {"true", "false"}
    assert len({q.source_start for q in quiz}) == len(quiz)  # one question per sentence
    methodology = REPORT[REPORT.index("The controller was built") : REPORT.index("Results")]
    focused = generate(seg, [methodology])
    in_methods = [q for q in focused if q.type != "viva" and q.explanation in methodology]
    assert len(in_methods) >= 3


def test_generate_is_deterministic_and_seed_varies(seg):
    a = [q.prompt for q in generate(seg)]
    assert a == [q.prompt for q in generate(seg)]
    b = [q.prompt for q in generate(seg, seed=7)]
    assert b == [q.prompt for q in generate(seg, seed=7)]
    assert len(b) >= 8


def test_assess_endpoints(client):
    r = client.post("/assess/generate", json={"text": REPORT})
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert qs and all(q["source_span"]["end"] > q["source_span"]["start"] for q in qs)
    closed = [q for q in qs if q["type"] != "viva"]
    answers = [{"id": q["id"], "answer": q["answer_key"]} for q in closed]
    g = client.post(
        "/assess/grade", json={"questions": closed, "answers": answers, "text": REPORT}
    ).json()
    assert g["total"] == 100.0

    v = client.post("/assess/viva/next", json={"text": REPORT, "history": []}).json()
    assert v["done"] is False and v["index"] == 1 and v["question"]["type"] == "viva"
    assert v["difficulty"] == "Define"
    graded = client.post(
        "/assess/grade",
        json={
            "questions": [v["question"]],
            "answers": [{"id": v["question"]["id"], "answer": "I am not sure."}],
        },
    ).json()
    assert graded["results"][0]["correct"] is None and graded["results"][0]["score"] < 40

    t = client.post(
        "/teachback", json={"text": REPORT, "explanation": "It was about farming."}
    ).json()
    assert 0 <= t["coverage"] <= 100 and t["missed"]


def test_assess_word_limit(client):
    big = "word " * 3001
    assert client.post("/assess/generate", json={"text": big}).status_code == 413
    assert client.post("/teachback", json={"text": big, "explanation": "x"}).status_code == 413
