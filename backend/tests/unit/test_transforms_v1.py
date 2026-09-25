"""Unit tests for P2 transforms: each must fire where it should and stay quiet otherwise."""

from __future__ import annotations

from app.core.protect import detect_protected
from app.core.segment import segment
from app.core.spans import Edit, SpanIndex, apply_edits
from app.humanize.edits import local_rewrite, minimal_edit
from app.humanize.text_utils import article_for, capitalize_first, lower_first
from app.humanize.transforms import phrase_simplify, split_long, synonym, transition_vary
from app.humanize.types import HumanizeContext


def ctx_for(text: str, tone: str = "academic") -> HumanizeContext:
    seg = segment(text)
    idx = SpanIndex((p.start, p.end) for p in detect_protected(text))
    return HumanizeContext(seg=seg, protected=idx, tone=tone, intensity=3)


def texts(module, text: str, sentence: int = 0, tone: str = "academic", prepare=None) -> list[str]:
    ctx = ctx_for(text, tone)
    if prepare:
        prepare(ctx)
    view = ctx.view(ctx.seg.sentences[sentence])
    return [c.text for c in module.apply(view, ctx)]


# ------------------------------------------------------------------ helpers


def test_minimal_edit_word_boundaries():
    assert minimal_edit("We utilize it.", "We use it.") == (3, 10, "use")
    assert minimal_edit("same", "same") is None


def test_local_rewrite_deletion_capitalises():
    t = "It is important to note that sensors work."
    e = local_rewrite(t, 0, 29, "", "phrase_simplify", "transform.phrase_simplify.delete", old="x")
    assert apply_edits(t, [Edit(e.start, e.end, e.replacement)]) == "Sensors work."


def test_local_rewrite_parenthetical_commas():
    t = "The motor, basically, works well."
    e = local_rewrite(t, 11, 20, "", "phrase_simplify", "transform.phrase_simplify.filler", old="x")
    assert apply_edits(t, [Edit(e.start, e.end, e.replacement)]) == "The motor works well."


def test_article_for():
    assert article_for("apple") == "an"
    assert article_for("useful") == "a"
    assert article_for("hour") == "an"
    assert article_for("LED") == "an"
    assert article_for("PLC") == "a"


def test_case_helpers():
    assert capitalize_first("  the pump") == "  The pump"
    assert lower_first("The pump") == "the pump"
    assert lower_first("IoT sensors") == "IoT sensors"


# ------------------------------------------------------------------ phrase_simplify


def test_phrase_simplify_wordy():
    assert "We use a pump to move water." in texts(
        phrase_simplify, "We use a pump in order to move water."
    )


def test_phrase_simplify_deletes_stock_opener():
    out = texts(phrase_simplify, "It is important to note that the valve leaks.")
    assert "The valve leaks." in out


def test_phrase_simplify_inflects():
    out = texts(phrase_simplify, "The team made a decision to stop the test.")
    assert "The team decided to stop the test." in out


def test_phrase_simplify_gerund_after_to():
    out = texts(phrase_simplify, "A clamp is used for the purpose of holding the part.")
    assert "A clamp is used to hold the part." in out


def test_phrase_simplify_skips_quotes():
    assert (
        texts(phrase_simplify, 'The manual says "in order to reset, hold the button" twice.') == []
    )


def test_phrase_simplify_quiet_on_plain_text():
    assert texts(phrase_simplify, "The pump moves water to the tank.") == []


# ------------------------------------------------------------------ synonym


def test_synonym_plainer_word():
    out = texts(synonym, "The team scrutinized the readings from the logger.")
    assert out and all(
        "scrutinized" not in t for t in out
    ), "expected a plainer synonym for a formal verb"


def test_synonym_never_swaps_nouns():
    def prep(ctx):
        ctx.recent_lemmas.append({"moisture", "sensor"})

    out = texts(
        synonym, "A. The soil moisture sensor reads the moisture level.", sentence=1, prepare=prep
    )
    assert all("moisture" in t for t in out)


def test_synonym_repeated_word_varied():
    text = "The first motor was big. The second motor was big too."

    def prep(ctx):
        ctx.recent_lemmas.append({"big", "motor"})

    out = texts(synonym, text, sentence=1, prepare=prep)
    assert any(" big " not in t for t in out)


def test_synonym_leaves_common_words():
    assert texts(synonym, "The pump moves water to the tank.") == []


def test_synonym_never_touches_protected_terms():
    text = "The PLC reads the MOSFET gate."
    for t in texts(synonym, text):
        assert "PLC" in t and "MOSFET" in t


def test_synonym_respects_once_per_paragraph():
    text = "Engineers endeavour to finish. They endeavour again."
    ctx = ctx_for(text)
    ctx.swapped_lemmas[0] = {"endeavour", "endeavor"}
    view = ctx.view(ctx.seg.sentences[1])
    assert all("endeavour" in c.text for c in synonym.apply(view, ctx))


# ------------------------------------------------------------------ transition_vary


def test_transition_repeated_is_varied():
    text = "Moreover, the pump runs. Moreover, the valve opens."

    def prep(ctx):
        ctx.chosen_openers.append("moreover")

    out = texts(transition_vary, text, sentence=1, prepare=prep)
    assert out and all(not t.startswith("Moreover") for t in out)
    assert "The valve opens." in out


def test_transition_first_use_kept():
    assert texts(transition_vary, "However, the pump failed.") == []


def test_transition_density():
    def prep(ctx):
        ctx.chosen_openers.extend(["", "therefore"])

    out = texts(transition_vary, "In addition, the tank filled.", prepare=prep)
    assert out


def test_transition_ignores_non_transitions():
    def prep(ctx):
        ctx.chosen_openers.extend(["however", "however"])

    assert texts(transition_vary, "The tank filled quickly.", prepare=prep) == []


def test_transition_alternatives_same_group():
    alts = transition_vary.alternatives("moreover", "academic", set())
    assert "furthermore" in alts or "in addition" in alts
    assert "however" not in alts


# ------------------------------------------------------------------ split_long


LONG_CC = (
    "The prototype was assembled on a wooden base with four bolts and a steel bracket, and the "
    "students then measured the output voltage at five different wind speeds in the lab."
)


def test_split_long_at_cc():
    out = texts(split_long, LONG_CC)
    assert any(". The students then measured" in t for t in out)


def test_split_long_relative_clause():
    text = (
        "The team replaced the small aluminium heat sink on the voltage regulator with a much "
        "larger copper one during the second week of testing, which reduced the peak "
        "temperature considerably."
    )
    out = texts(split_long, text)
    assert any(". This reduced the peak temperature" in t for t in out)


def test_split_long_ignores_short_sentences():
    assert texts(split_long, "The pump failed, and the valve stuck.") == []


def test_split_long_needs_independent_clauses():
    text = (
        "The students measured the voltage and current of the small solar panel at noon on three "
        "consecutive sunny days in the university car park with a digital multimeter."
    )
    assert texts(split_long, text) == []


def test_split_long_but_becomes_however():
    text = (
        "The first design used a single low-cost bearing on the drive shaft of the small conveyor, "
        "but the second design needed two bearings because the load on the shaft was higher."
    )
    out = texts(split_long, text)
    assert any(". However, the second design" in t for t in out)


# ------------------------------------------------------------------ ranking gates


def test_fluency_gate_rejects_scrambled_rewrite():
    from app.humanize.ranking.scorer import score_candidates
    from app.humanize.ranking.style_fit import StyleTargets
    from app.humanize.types import Candidate, LocalEdit

    text = "The results show that the motor speed increases with the supply voltage."
    seg = segment(text)
    sent = seg.sentences[0]
    scrambled = "results the show motor that the with increases speed supply"
    edit = LocalEdit(4, 71, scrambled, "synonym", "x", "vocabulary")
    cand = Candidate(edits=(edit,), transforms=("synonym",), text=text[:4] + scrambled + text[71:])
    orig = Candidate(edits=(), transforms=(), text=text)
    score_candidates(orig, [cand], sent.span.as_doc(), StyleTargets())
    assert cand.rejected in {"fluency", "meaning"}


def test_meaning_gate_rejects_content_change():
    from app.humanize.ranking.scorer import score_candidates
    from app.humanize.ranking.style_fit import StyleTargets
    from app.humanize.types import Candidate, LocalEdit

    text = "The copper bracket carries the heavy gearbox on the test rig."
    seg = segment(text)
    new = "banana orchard sings loudly beside purple"
    edit = LocalEdit(4, 44, new, "synonym", "x", "vocabulary")
    cand = Candidate(edits=(edit,), transforms=("synonym",), text=text[:4] + new + text[44:])
    orig = Candidate(edits=(), transforms=(), text=text)
    score_candidates(orig, [cand], seg.sentences[0].span.as_doc(), StyleTargets())
    assert cand.rejected == "meaning"
