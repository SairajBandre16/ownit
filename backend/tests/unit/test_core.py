from __future__ import annotations

import pytest

from app.core.lexicon import PhraseLexicon, inflect, lexicon, match_case
from app.core.segment import canonical_section, looks_like_heading, segment, split_paragraphs
from app.core.spans import Edit, SpanIndex, apply_edits, diff_hunks, merge_spans, overlaps

# ------------------------------------------------------------------ spans


def test_overlaps_half_open():
    assert overlaps(0, 5, 4, 8)
    assert not overlaps(0, 5, 5, 8)
    assert not overlaps(5, 8, 0, 5)


def test_merge_spans_joins_touching_and_overlapping():
    assert merge_spans([(5, 8), (0, 3), (2, 5), (10, 12)]) == [(0, 8), (10, 12)]
    assert merge_spans([(3, 3)]) == []


def test_span_index_queries():
    idx = SpanIndex([(10, 20), (30, 40)])
    assert idx.overlaps(15, 16)
    assert idx.overlaps(5, 11)
    assert not idx.overlaps(20, 30)
    assert idx.covered(31, 39)
    assert not idx.covered(25, 35)


def test_apply_edits_any_order():
    text = "in order to use it"
    edits = [Edit(12, 15, "apply"), Edit(0, 11, "to")]
    assert apply_edits(text, edits) == "to apply it"
    with pytest.raises(ValueError):
        apply_edits(text, [Edit(0, 5, "x"), Edit(3, 6, "y")])


def test_diff_hunks_word_level():
    a = "We utilize the sensor in order to measure heat."
    b = "We use the sensor to measure heat."
    hunks = diff_hunks(a, b)
    assert [(h.original.strip(), h.replacement.strip()) for h in hunks] == [
        ("utilize", "use"),
        ("in order", ""),
    ]
    for h in hunks:
        assert a[h.orig_start : h.orig_end] == h.original
        assert b[h.new_start : h.new_end] == h.replacement


def test_diff_hunks_identical_is_empty():
    assert diff_hunks("same text.", "same text.") == []


# ------------------------------------------------------------------ segment


@pytest.mark.parametrize(
    ("heading", "name"),
    [
        ("Introduction", "introduction"),
        ("2. Materials and Methods", "methodology"),
        ("3.1 Experimental Setup", "methodology"),
        ("RESULTS AND DISCUSSION", "discussion"),
        ("## Conclusions", "conclusion"),
        ("References", "references"),
    ],
)
def test_canonical_section(heading, name):
    assert canonical_section(heading) == name


def test_not_headings():
    assert not looks_like_heading("The motor was tested at 50 Hz.")
    assert not looks_like_heading(
        "This is a long line that clearly is a sentence of prose, not a title"
    )
    assert looks_like_heading("Circuit Design")
    assert looks_like_heading("4. Results")


def test_split_paragraphs_blank_lines_and_headings():
    text = "Introduction\nFirst para line one.\nline two.\n\nSecond para."
    paras = split_paragraphs(text)
    assert [p.is_heading for p in paras] == [True, False, False]
    assert paras[1].text == "First para line one.\nline two."
    for p in paras:
        assert text[p.start : p.end] == p.text


def test_segment_sentences_and_sections():
    text = (
        "Introduction\nMotors convert energy. They are common.\n\n"
        "Methodology\nThe rig was built. As shown in Fig. 2, the load was applied."
    )
    seg = segment(text)
    assert [s.name for s in seg.sections] == ["introduction", "methodology"]
    body = seg.body_sentences
    assert [s.text for s in body] == [
        "Motors convert energy.",
        "They are common.",
        "The rig was built.",
        "As shown in Fig. 2, the load was applied.",
    ]
    assert body[2].section == "methodology"
    for s in seg.sentences:
        assert text[s.start : s.end] == s.text


def test_segment_without_headings_is_body():
    seg = segment("Just one paragraph. Two sentences.")
    assert seg.sections[0].name == "body"
    assert len(seg.body_sentences) == 2


# ------------------------------------------------------------------ lexicon


def test_lexicon_inflects_placeholder():
    lx = PhraseLexicon({"{make} a decision": "{decide}"})
    for text, expected in [
        ("We made a decision.", "decided"),
        ("They make a decision.", "decide"),
        ("She makes a decision.", "decides"),
        ("Making a decision is hard.", "Deciding"),
    ]:
        (m,) = lx.find(text)
        assert PhraseLexicon.render(m.value, m) == expected


def test_lexicon_word_boundaries_and_quotes():
    lx = PhraseLexicon({"in order to": "to", "today's world": "today"})
    assert lx.find("reordering to") == []
    assert len(lx.find("In order to go")) == 1
    assert len(lx.find("in today’s world")) == 1
    assert lx.find("in-order-to") == []


def test_lexicon_longest_match_wins():
    lx = lexicon("wordy_phrases")
    (m,) = [m for m in lx.find("due to the fact that it rained") if m.start == 0]
    assert m.key == "due to the fact that"


def test_inflect_and_case():
    assert inflect("show", "VBZ") == "shows"
    assert inflect("use", None) == "use"
    assert match_case("to", "In order to") == "To"
    assert match_case("to", "IN ORDER TO") == "TO"


def test_resource_sizes():
    from app.core.resources import load

    assert len([k for k in load("wordy_phrases") if not k.startswith("_")]) >= 300
    assert len(load("ai_style_phrases")) >= 300
    assert len([k for k in load("cliches") if not k.startswith("_")]) >= 300
    assert len([k for k in load("fillers") if not k.startswith("_")]) >= 300
    assert len(load("hedges")["hedges"]) >= 300
    assert len([k for k in load("weak_verbs") if not k.startswith("_")]) >= 300
    assert sum(len(v) for v in load("transitions")["groups"].values()) >= 300
    assert len(load("eng_abbreviations")) >= 300
    si = load("si_units")
    assert len(si["units"]) + len(si["miscased"]) + len(si["plurals"]) >= 300
