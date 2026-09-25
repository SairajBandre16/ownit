"""Unit tests for P4: gist, glossary, simplify offset mapping, concept map, /walkthrough."""

from __future__ import annotations

from types import SimpleNamespace

from app.core.nlp import parse
from app.core.segment import segment
from app.walkthrough import concept_map
from app.walkthrough.gist import compress, gist
from app.walkthrough.glossary import (
    _definition_in_text,
    abbreviation_pairs,
    document_definitions,
    expansion_for,
    paragraph_terms,
    wordnet_definition,
)
from app.walkthrough.simplify import map_offset

REPORT = (
    "Introduction\n"
    "A programmable logic controller (PLC) is an industrial computer that controls machines in "
    "real time. In today's fast-paced world, it is important to note that the PLC plays a crucial "
    "role in factory automation. The PLC reads sensor inputs and drives actuators such as motors "
    "and valves.\n\n"
    "Methodology\n"
    "The temperature sensor measures the water temperature every second. The PLC compares this "
    "value with the set point and switches the heater. A proportional controller was used because "
    "it is simple to tune. The heater was driven by a solid state relay rated at 25 A.\n\n"
    "Results\n"
    "The water reached 60 °C in 14 minutes (Fig. 2). The overshoot was 1.5 °C, which is acceptable "
    "for this process. The PLC kept the temperature within ±0.5 °C of the set point for the rest "
    "of the test.\n"
)


def sents(text: str):  # type: ignore[no-untyped-def]
    return segment(text).sentences


# --- gist -----------------------------------------------------------------------------------


def test_gist_drops_relative_clause_and_parenthetical():
    g = gist(sents("The water reached 60 °C in 14 minutes (Fig. 2)."))
    assert "Fig" not in g and "2)" not in g
    assert g.startswith("The water reached 60 °C")
    assert g.endswith(".")


def test_gist_keeps_figure_reference_whole():
    g = gist(
        sents("The circuit shown in Fig. 3 uses an LM317 voltage regulator to fix the output.")
    )
    assert "Fig. 3" in g or "Fig" not in g


def test_gist_keeps_noun_coordination():
    g = gist(
        sents("The water sample from the college borewell was analysed for pH, TDS and hardness.")
    )
    assert "TDS and hardness" in g


def test_gist_does_not_end_on_function_word():
    g = gist(
        sents(
            "Wireless sensor networks consist of many small sensor nodes that monitor physical "
            "conditions such as temperature and humidity."
        )
    )
    assert not g.rstrip(".").endswith(("consist", "of", "how"))
    assert "sensor nodes" in g


def test_gist_skips_heading_fragments_and_stock_phrases():
    g = gist(
        sents(
            "Results. It is important to note that the yield strength of the alloy was 276 MPa. "
            "The elongation at break was 12 %."
        )
    )
    assert g != "Results."
    assert "important to note" not in g


def test_gist_hyphenated_words_stay_whole():
    g = gist(sents("3D printing has emerged as a game-changing technology for rapid prototyping."))
    assert "-changing" not in g.replace("game-changing", "")


def test_compress_short_sentence_unchanged_meaning():
    span = parse("The pump stopped.")[:]
    assert compress(span).startswith("The pump stopped")


# --- glossary -------------------------------------------------------------------------------


def test_expansion_for_trims_leading_words():
    assert expansion_for("A programmable logic controller".split(), "PLC") == (
        "programmable logic controller"
    )
    assert expansion_for("uses the Internet of Things".split(), "IoT") == "Internet of Things"
    assert expansion_for("we used a".split(), "PWM") is None


def test_abbreviation_pairs_and_document_definitions():
    seg = segment(REPORT)
    assert abbreviation_pairs(seg) == {"PLC": "programmable logic controller"}
    defs = document_definitions(seg)
    assert defs["plc"] == "programmable logic controller"
    assert defs["programmable logic controller"] == "abbreviated as PLC"


def test_definition_in_text_patterns():
    assert _definition_in_text(
        "PLC", "Intro. The PLC is an industrial computer that runs code."
    ) == ("an industrial computer that runs code")
    text = "The Seebeck effect refers to the voltage produced across two dissimilar metals."
    assert _definition_in_text("Seebeck effect", text) == (
        "the voltage produced across two dissimilar metals"
    )


def test_definition_in_text_must_not_fire():
    # a word inside a longer term does not take the longer term's definition
    assert (
        _definition_in_text("congestion", "Traffic congestion is a major problem in cities.")
        is None
    )
    # an all-caps abbreviation never matches the verb "is"
    assert _definition_in_text("IS", "It is a powerful tool that engineers use daily.") is None
    # definitions that are too short are ignored
    assert _definition_in_text("valve", "The valve is a part.") is None


def test_wordnet_rejects_off_domain_and_unsupported_senses():
    assert wordnet_definition("set point", frozenset({"temperature", "heater"})) is None  # tennis
    assert wordnet_definition("overshoot", frozenset({"temperature"})) is None  # wrong sense
    assert wordnet_definition("zzqx widget") is None


def test_wordnet_accepts_multiword_term():
    d = wordnet_definition("turbulent flow", frozenset({"velocity", "pipe"}))
    assert d and "flow" in d


def test_paragraph_terms_offsets_and_sources():
    seg = segment(REPORT)
    p = next(p for p in seg.paragraphs if not p.is_heading)
    terms = paragraph_terms(seg, p.start, p.end, document_definitions(seg))
    assert terms and len(terms) <= 5
    for t in terms:
        assert REPORT[t.start : t.end] == t.term
    by_term = {t.term: t for t in terms}
    assert by_term["PLC"].definition == "programmable logic controller"
    assert by_term["programmable logic controller"].source == "document"


def test_paragraph_terms_skip_units_and_section_names():
    text = (
        "Methodology. The specimen was loaded at a rate of 2 mm/min in the universal testing "
        "machine. The extensometer measured the elongation of the gauge length."
    )
    seg = segment(text)
    terms = {t.term.lower() for t in paragraph_terms(seg, 0, len(text), {})}
    assert "min" not in terms and "methodology" not in terms
    assert "universal testing machine" in terms


# --- simplify offset mapping ------------------------------------------------------------------


def change(os_: int, oe: int, ns: int, ne: int):  # type: ignore[no-untyped-def]
    return SimpleNamespace(orig_start=os_, orig_end=oe, new_start=ns, new_end=ne)


def test_map_offset_shifts_after_changes():
    # "in order to" (3..14) -> "to" (3..5): later offsets shift by -9
    changes = [change(3, 14, 3, 5)]
    assert map_offset(0, changes) == 0
    assert map_offset(20, changes) == 11
    assert map_offset(14, changes, "end") == 5


def test_map_offset_inside_change_snaps_to_edges():
    changes = [change(10, 20, 10, 12)]
    assert map_offset(15, changes, "start") == 10
    assert map_offset(15, changes, "end") == 12


def test_map_offset_start_at_change_start_not_shifted():
    changes = [change(10, 20, 10, 25)]
    assert map_offset(10, changes, "start") == 10
    assert map_offset(20, changes, "end") == 25


# --- concept map ------------------------------------------------------------------------------


def test_concept_map_merges_abbreviation_and_links_verbs():
    seg = segment(REPORT)
    body = [p.index for p in seg.paragraphs if not p.is_heading]
    cmap = concept_map.build(seg, body)
    labels = [n.label for n in cmap.nodes]
    assert "PLC" in labels
    assert "programmable logic controller" not in labels
    assert "tune" not in labels
    ids = {n.id for n in cmap.nodes}
    for e in cmap.edges:
        assert e.source in ids and e.target in ids
    assert any(e.label == "measure" for e in cmap.edges)
    assert not any(e.label in ("play", "be", "have") for e in cmap.edges)
    for n in cmap.nodes:
        assert 0 <= n.x <= 1 and 0 <= n.y <= 1 and 0 < n.weight <= 1
        assert set(n.paragraphs) <= set(body)


def test_concept_map_is_deterministic():
    seg = segment(REPORT)
    body = [p.index for p in seg.paragraphs if not p.is_heading]
    a, b = concept_map.build(seg, body), concept_map.build(seg, body)
    assert [(n.id, n.x, n.y) for n in a.nodes] == [(n.id, n.x, n.y) for n in b.nodes]


def test_concept_map_empty_text():
    seg = segment("Hello there.")
    assert concept_map.build(seg, []).nodes == []


# --- endpoint ---------------------------------------------------------------------------------


def test_walkthrough_endpoint(client):
    r = client.post("/walkthrough", json={"text": REPORT})
    assert r.status_code == 200
    data = r.json()
    paras = data["paragraphs"]
    assert len(paras) == 3  # headings are not paragraphs to walk through
    assert [p["section"] for p in paras] == ["introduction", "methodology", "results"]
    for p in paras:
        assert p["gist"] and p["gist"][-1] in ".…"
        assert REPORT[p["start"] : p["end"]].strip()
        assert p["simplified"]
        for t in p["key_terms"]:
            assert REPORT[t["start"] : t["end"]] == t["term"]
    assert "important to note" not in paras[0]["simplified"]
    assert data["concept_map"]["nodes"]


def test_walkthrough_endpoint_word_limit(client):
    assert client.post("/walkthrough", json={"text": "word " * 3001}).status_code == 413


# --- title lines and whole-compound terms -----------------------------------------------------


def test_is_title_line():
    from app.walkthrough.service import is_title_line

    assert is_title_line("Design and Testing of a Smart Irrigation Controller")
    assert not is_title_line("The pump was switched by a relay module rated at 10 A.")
    assert not is_title_line(" ".join(["word"] * 20))


def test_walkthrough_skips_document_title():
    from app.walkthrough.service import walkthrough

    r = walkthrough("Design of a Solar Tracker\n\n" + REPORT)
    assert all("Solar Tracker" not in p.gist for p in r.paragraphs)
    assert len(r.paragraphs) == 3


def test_keyphrases_expand_to_whole_compound():
    from app.core.terms import noun_keyphrases

    text = (
        "A capacitive soil moisture sensor was used to measure the volumetric water content. "
        "The capacitive soil moisture sensor was calibrated against oven-dried samples."
    )
    terms = [t.lower() for t, _, _ in noun_keyphrases(segment(text), top=8)]
    assert "capacitive soil moisture sensor" in terms
    assert not any(t in ("capacitive soil", "moisture sensor", "soil moisture") for t in terms)
