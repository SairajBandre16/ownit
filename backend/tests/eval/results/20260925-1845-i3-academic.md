# Humanize evaluation — 2026-09-25 18:45

intensity=3 · tone=academic · LanguageTool=on · LM=fallback

| group | paragraphs | meaning_sim | min_meaning_sim | new_grammar_errors | fk_grade_change | score_change | pct_sentences_changed | sec_per_1000_words | doc_sec_per_1000_words |
|---|---|---|---|---|---|---|---|---|---|
| all | 97 | 0.973 | 0.915 | 0 | -0.215 | 2.481 | 50.552 | 1.698 | 0.812 |
| ai | 34 | 0.951 | 0.915 | 0 | -0.297 | 3.621 | 75.000 | 2.768 | 1.033 |
| engineering | 32 | 0.973 | 0.944 | 0 | -0.290 | 2.922 | 51.493 | 1.233 | 0.808 |
| student | 31 | 0.997 | 0.984 | 0 | -0.048 | 0.777 | 13.043 | 0.824 | 0.506 |

Targets: new_grammar_errors = 0 · meaning_sim ≥ 0.80 per sentence (gate) · doc_sec_per_1000_words < 3 on the free CPU. sec_per_1000_words is per-paragraph requests (~70 words each), dominated by fixed per-request overhead.
