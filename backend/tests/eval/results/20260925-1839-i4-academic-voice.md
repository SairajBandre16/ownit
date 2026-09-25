# Humanize evaluation — 2026-09-25 18:39

intensity=4 · tone=academic · LanguageTool=on · LM=fallback

| group | paragraphs | meaning_sim | min_meaning_sim | new_grammar_errors | fk_grade_change | score_change | pct_sentences_changed | sec_per_1000_words | voice_match_before | voice_match_after | voice_match_improved_pct | doc_sec_per_1000_words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 34 | 0.967 | 0.909 | 0 | -0.515 | 1.700 | 72.059 | 5.566 | 17.150 | 17.615 | 55.882 | 1.275 |
| ai | 34 | 0.967 | 0.909 | 0 | -0.515 | 1.700 | 72.059 | 5.566 | 17.150 | 17.615 | 55.882 | 1.275 |

Targets: new_grammar_errors = 0 · meaning_sim ≥ 0.80 per sentence (gate) · doc_sec_per_1000_words < 3 on the free CPU. sec_per_1000_words is per-paragraph requests (~70 words each), dominated by fixed per-request overhead.
