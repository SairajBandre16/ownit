"""Unit tests for P7: the Engineering Report Doctor checks and /doctor."""

from __future__ import annotations

import pytest

from app.analyze.base import AnalyzerContext
from app.core.nlp import parse
from app.core.segment import segment
from app.doctor import abbreviations, claims, figures, structure, tense, units
from app.doctor.service import run_doctor


def ctx(text: str) -> AnalyzerContext:
    return AnalyzerContext.build(segment(text))


def rules(check, text: str) -> list[str]:  # type: ignore[no-untyped-def]
    return [i.rule for i in check(ctx(text))]


def quote(check, text: str, rule: str) -> list[str]:  # type: ignore[no-untyped-def]
    return [text[i.start : i.end] for i in check(ctx(text)) if i.rule == rule]


# --- units --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "rule", "suggestion"),
    [
        ("The supply was 12V in every test run.", "units.spacing", "12 V"),
        ("The beam carried 25kN at mid-span.", "units.spacing", "25 kN"),
        ("The frame weighs 5 KG in total.", "units.case", "5 kg"),
        ("The heater is rated at 2 kw for the tank.", "units.case", "2 kW"),
        ("The motor ran for 2 hrs without stopping.", "units.plural", "2 h"),
        ("The sample weighed 3 kgs after drying.", "units.plural", "3 kg"),
    ],
)
def test_unit_formatting(text, rule, suggestion):
    found = [i for i in units.check(ctx(text)) if i.rule == rule]
    assert len(found) == 1 and found[0].suggestion == suggestion


@pytest.mark.parametrize(
    "text",
    [
        "The supply was 12 V in every test run.",
        "The efficiency was 91%, and the angle was 45°.",
        "The ESP32 board and the LM317 regulator were used.",
        "The part number is 3M-2210 and the model is 5G-ready.",
        "The fan ran for 45 in the first trial and 50 in the second.",  # "in" is not inches
        "The code sets `delay(10ms)` before reading.",  # code is protected
    ],
)
def test_unit_formatting_must_not_fire(text):
    assert [r for r in rules(units.check, text) if r != "units.missing"] == []


def test_mixed_unit_systems():
    text = "The pipe is 3 m long. The cable is 12 ft long."
    assert quote(units.check, text, "units.mixed") == ["12 ft"]
    assert "units.mixed" not in rules(units.check, "The pipe is 3 m long. The cable is 12 m long.")
    assert "units.mixed" not in rules(
        units.check, "The pipe is 3 m long and weighs 2 lb."
    )  # different quantities


@pytest.mark.parametrize(
    "sentence",
    [
        "The peak power was 18.5 and it stayed there.",
        "The overshoot reached 1.5 during the run.",
        "The final reading was 230.",
    ],
)
def test_numbers_without_units_in_results(sentence):
    assert "units.missing" in rules(units.check, f"Results\n{sentence}\n")


@pytest.mark.parametrize(
    "sentence",
    [
        "The peak power was 18.5 W.",
        "Five samples were tested and 3 samples failed.",
        "The COP was 2.4 for the second run.",
        "The pressure rose from 120 to 410 Pa over time.",
        "The results in Table 2 agree with the 2019 study.",
        "The efficiency was 91% at full load.",
    ],
)
def test_numbers_without_units_must_not_fire(sentence):
    assert "units.missing" not in rules(units.check, f"Results\n{sentence}\n")
    assert "units.missing" not in rules(
        units.check, "Introduction\nThe peak was 18.5 and it stayed.\n"
    )


# --- abbreviations ------------------------------------------------------------------------------


def test_abbreviation_used_before_definition():
    text = "The PLC controls the pump. A programmable logic controller (PLC) is an industrial computer. The PLC is cheap."
    issues = abbreviations.check(ctx(text))
    undefined = [i for i in issues if i.rule == "abbr.undefined"]
    assert len(undefined) == 1 and text[undefined[0].start : undefined[0].end] == "PLC"
    assert undefined[0].suggestion == "programmable logic controller (PLC)"


def test_abbreviation_never_defined_uses_known_expansion():
    issues = abbreviations.check(ctx("We used PWM to control the motor speed of the fan."))
    assert (
        issues[0].rule == "abbr.undefined"
        and issues[0].suggestion == "pulse-width modulation (PWM)"
    )


def test_abbreviation_defined_twice_and_unused():
    text = (
        "A light dependent resistor (LDR) senses light. The circuit uses a light dependent resistor (LDR) too. "
        "Pulse width modulation (PWM) sets the speed."
    )
    got = {(i.rule, text[i.start : i.end]) for i in abbreviations.check(ctx(text))}
    assert ("abbr.redefined", "light dependent resistor (LDR)") in got
    assert ("abbr.unused", "PWM") in got


@pytest.mark.parametrize(
    "text",
    [
        "A programmable logic controller (PLC) is used. The PLC reads the sensors every second.",
        "The LED and USB port are on the front panel of the box.",  # common abbreviations
        "The load was 25 kN and the supply 12 V throughout the test.",  # units are not abbreviations
        "Section II describes the setup and Section III the results.",  # Roman numerals
        "The model was drawn in SolidWorks and simulated in MATLAB and LabVIEW.",  # tool names
        "PLC (programmable logic controller) programs run in cycles. Each PLC scan takes 10 ms.",  # reverse form
    ],
)
def test_abbreviations_must_not_fire(text):
    assert rules(abbreviations.check, text) == []


def test_abstract_definition_may_be_repeated_in_body():
    text = (
        "Abstract\nA programmable logic controller (PLC) was used. The PLC ran well.\n\n"
        "Introduction\nA programmable logic controller (PLC) is an industrial computer. The PLC runs code.\n"
    )
    assert "abbr.redefined" not in rules(abbreviations.check, text)


# --- figures ------------------------------------------------------------------------------------


def test_figures_order_and_captions():
    text = (
        "Results\nFigure 2 shows the energy. Figure 1 compares the panels.\n"
        "Figure 1: Output of both panels.\nFigure 3: Wiring diagram.\n"
    )
    got = {(i.rule, text[i.start : i.end].split(":")[0]) for i in figures.check(ctx(text))}
    assert ("figures.order", "Figure 2") in got  # mentioned before Figure 1
    assert ("figures.missing", "Figure 2") in got  # no caption for Figure 2
    assert ("figures.unreferenced", "Figure 3") in got  # caption never mentioned
    assert ("figures.order", "Figure 3") in got  # captions jump 1 → 3


@pytest.mark.parametrize(
    "text",
    [
        "Fig. 1 shows the rig. Fig. 2 shows the output. Table 1 lists the parts.",
        "Figs. 1–3 show the rig from three sides, and Fig. 4 the circuit.",
        "Figure 1 shows the rig.\nFigure 1: Test rig.",
        "Table 1 lists the parts and Table 2 the costs.\nTable 1: Parts.\nTable 2: Costs.",
        "The rig is described in Section 2 and in Eq. (3).",
    ],
)
def test_figures_must_not_fire(text):
    assert rules(figures.check, text) == []


def test_references_without_any_captions_are_not_reported():
    # pasted text often has no captions at all
    assert rules(figures.check, "Fig. 1 shows the rig and Fig. 2 shows the output.") == []


# --- tense --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("The sample was heated to 60 °C.", "past"),
        ("The sample is heated to 60 °C.", "present"),
        ("We measured the voltage.", "past"),
        ("The sensor measures the voltage.", "present"),
        ("The controller will switch the pump.", "present"),
    ],
)
def test_sentence_tense(sentence, expected):
    assert tense.sentence_tense(parse(sentence)[:]) == expected


def test_tense_outlier_in_methodology():
    text = (
        "Methodology\nThe frame was cut from aluminium. The motors were mounted on the frame. "
        "The wires were soldered to the board. The data is logged every second.\n"
    )
    assert quote(tense.check, text, "tense.outlier") == ["The data is logged every second."]


def test_whole_section_in_the_other_tense_gets_one_note():
    text = (
        "Methodology\nThe frame is cut from aluminium. The motors are mounted on the frame. "
        "The wires are soldered to the board. The code is uploaded.\n"
    )
    assert rules(tense.check, text) == ["tense.section"]


@pytest.mark.parametrize(
    "text",
    [
        "Results\nThe current rose to 2 A. The voltage fell to 11 V. Table 2 shows the full data. The fan stopped at noon.\n",
        "Introduction\nSolar panels convert light. Trackers follow the sun. In 1954, Bell Labs demonstrated the first cell. Panels are cheap now.\n",
        "Introduction\nSolar panels convert light. Trackers follow the sun. Rao et al. (2019) proposed a tracker. Panels are cheap now.\n",
        "Methodology\nThe frame was cut. The motors were mounted. Fig. 2 shows the frame. The wires were soldered.\n",
        "Discussion\nThe result is good. The tracker worked. It was cheap. It is robust.\n",  # not a checked section
    ],
)
def test_tense_must_not_fire(text):
    assert rules(tense.check, text) == []


# --- claims -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "marker"),
    [
        ("Tracking always gives the best output for panels.", "always"),
        ("The results clearly show that the design works well.", "clearly show"),
        ("This proves that the controller is reliable.", "proves"),
        ("The new layout significantly improves output.", "significantly"),
        ("Undoubtedly, this is the most efficient approach here.", "Undoubtedly"),
    ],
)
def test_unsupported_claims(text, marker):
    assert quote(claims.check, text, "claims.unsupported") == [marker]


@pytest.mark.parametrize(
    "text",
    [
        "Tracking always gives more output (Rao, 2019).",
        "The results clearly show a 27% gain in output.",
        "The results clearly show the trend in Fig. 3.",
        "The new layout significantly improves output. Output rose from 12 W to 18 W.",
        "The tracker gives more output than a fixed panel in summer.",
        'The manual says "this always works" in its first chapter.',
    ],
)
def test_claims_must_not_fire(text):
    assert rules(claims.check, text) == []


# --- structure ----------------------------------------------------------------------------------


def test_structure_missing_and_order():
    text = (
        "Solar Tracker Report\n\nIntroduction\nText here.\n\nResults\nThe output rose.\n\n"
        "Methodology\nThe frame was cut.\n\nConclusion\nIt worked.\n"
    )
    got = {(i.rule, i.message) for i in structure.check(ctx(text))}
    assert any(
        r == "structure.order" and "'Methodology' usually comes after 'Results'" in m
        for r, m in got
    )
    assert any(r == "structure.missing" and "References" in m for r, m in got)


def test_long_abstract():
    text = "Abstract\n" + "word " * 260 + "\n\nIntroduction\nText.\n\nConclusion\nDone.\n"
    assert "structure.abstract_long" in rules(structure.check, text)


@pytest.mark.parametrize(
    "text",
    [
        "Renewable energy is growing. Solar power is cheap. Wind power is too.",  # an essay
        "Introduction\nText.\n\nMethodology\nText.\n\nResults and Discussion\nText.\n\nConclusion\nText.\n\nReferences\n[1] A.",
        "Design of a Solar Tracker\n\nIntroduction\nText.\n\nMethodology\nText.\n\nResults\nText.\n\nConclusion\nText.\n\nReferences\n[1] A.",
        "Abstract\nShort.\n\nIntroduction\nText.\n\nMethods\nText.\n\nResults\nText.\n\nConclusions and future work\nText.\n\nBibliography\n[1] A.",
        "Introduction\nText only, one heading.",
    ],
)
def test_structure_must_not_fire(text):
    assert rules(structure.check, text) == []


# --- service + endpoint ---------------------------------------------------------------------------


def test_run_doctor_counts_by_check():
    text = "Results\nThe supply was 12V. The PLC always works.\n"
    issues, counts = run_doctor(text)
    assert all(i.category == "engineering" for i in issues)
    assert counts["units"] == 1 and counts["abbreviations"] == 1 and counts["claims"] == 1
    assert set(counts) == {"units", "abbreviations", "figures", "tense", "claims", "structure"}


def test_doctor_endpoint(client):
    r = client.post("/doctor", json={"text": "The supply was 12V throughout."})
    assert r.status_code == 200
    body = r.json()
    assert (
        body["issues"][0]["rule"] == "units.spacing" and body["issues"][0]["suggestion"] == "12 V"
    )
    assert body["issues"][0]["lesson_slug"] == "units"
    assert client.post("/doctor", json={"text": "word " * 3001}).status_code == 413
