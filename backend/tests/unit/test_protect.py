from __future__ import annotations

import itertools

import pytest

from app.core.protect import protected_index, protected_spans


def kinds(text: str, keep: tuple[str, ...] = ()) -> dict[str, str]:
    return {p.text: p.kind for p in protected_spans(text, keep)}


@pytest.mark.parametrize(
    ("text", "span", "kind"),
    [
        ('He said "the load is safe" twice.', '"the load is safe"', "quote"),
        ("He said “the load is safe” twice.", "“the load is safe”", "quote"),
        ("Steel is strong (Smith, 2021).", "(Smith, 2021)", "citation"),
        ("Steel is strong (Smith et al., 2021).", "(Smith et al., 2021)", "citation"),
        ("Steel is strong [3].", "[3]", "citation"),
        ("Steel is strong [3–5].", "[3–5]", "citation"),
        ("The value $E = mc^2$ holds.", "$E = mc^2$", "equation"),
        ("A load of 25 kN was applied.", "25 kN", "number"),
        ("It runs at 3.3V today.", "3.3V", "number"),
        ("Tolerance is ±0.2 mm here.", "±0.2 mm", "number"),
        ("The pressure was 10^5 Pa.", "10^5 Pa", "number"),
        ("Efficiency rose by 12%.", "12%", "number"),
        ("Call `np.fft.fft` first.", "`np.fft.fft`", "code"),
        ("See Fig. 3 for details.", "Fig. 3", "reference"),
        ("See Figure 2(a) for details.", "Figure 2(a)", "reference"),
        ("Values are in Table 1 now.", "Table 1", "reference"),
        ("Apply Eq. (4) here.", "Eq. (4)", "reference"),
        ("The PLC controls it.", "PLC", "abbreviation"),
        ("An IoT node sends data.", "IoT", "abbreviation"),
    ],
)
def test_protected_kinds(text, span, kind):
    found = kinds(text)
    assert found.get(span) == kind, found


def test_keep_terms_are_protected_case_insensitively():
    found = kinds("The Heat Sink cools. A heat sink is metal.", ("heat sink",))
    assert "Heat Sink" in found and "heat sink" in found


def test_named_entities():
    found = kinds("Engineers at Tata Motors in Pune tested it.")
    assert any(k == "entity" for k in found.values())


def test_plain_prose_mostly_unprotected():
    text = "The students wrote a short report about bridges and how they carry loads."
    idx = protected_index(text)
    start = text.index("wrote")
    assert not idx.overlaps(start, start + 5)


def test_protected_spans_are_disjoint_and_match_text():
    text = "The PLC (Smith, 2021) at 5 kN reads $x=1$ and Fig. 2 shows [4]."
    spans = protected_spans(text)
    for a, b in itertools.pairwise(spans):
        assert a.end <= b.start
    for p in spans:
        assert text[p.start : p.end] == p.text


def test_hyphenated_words_are_not_equations():
    found = kinds("A state-of-the-art, well-known method.")
    assert "equation" not in found.values()
