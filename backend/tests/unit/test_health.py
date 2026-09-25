from __future__ import annotations

from app.humanize.ranking.fluency import fluency_drop, fluency_norm, get_fluency_scorer, tokenize


def test_health_reports_components(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["spacy"].startswith("en_core_web_md")
    assert body["lm"] in {"kenlm", "fallback"}
    assert isinstance(body["languagetool"], bool)


def test_tokenize_normalises_numbers_and_clitics():
    assert tokenize("The motor's speed was 1,500 rpm.") == [
        "the",
        "motor's",
        "speed",
        "was",
        "<num>",
        "rpm",
        ".",
    ]


def test_fluency_norm_is_centered_on_original():
    assert fluency_norm(-3.0, -3.0) == 0.5
    assert fluency_norm(-3.0, -2.0) == 1.0
    assert fluency_norm(-3.0, -5.0) == 0.0


def test_fluency_drop():
    assert abs(fluency_drop(-2.0, -2.3) - 0.15) < 1e-9
    assert fluency_drop(-2.0, -1.5) == 0.0


def test_lm_prefers_fluent_order():
    lm = get_fluency_scorer()
    if not lm.ready:
        return
    good = lm.score("The results show that the speed increases with voltage.")
    bad = lm.score("Results the show speed that the with increases voltage.")
    assert good > bad
