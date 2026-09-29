# Humanize evaluation: 2026-09-25 18:33

intensity=4 · tone=academic · LanguageTool=on · LM=fallback

| group | paragraphs | meaning_sim | min_meaning_sim | new_grammar_errors | fk_grade_change | score_change | pct_sentences_changed | sec_per_1000_words | voice_match_before | voice_match_after | voice_match_improved_pct | doc_sec_per_1000_words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 97 | 0.974 | 0.922 | 0 | -0.219 | 2.370 | 51.381 | 4.916 | 24.862 | 21.554 | 12.371 | 3.351 |
| ai | 34 | 0.953 | 0.922 | 0 | -0.323 | 3.335 | 75.000 | 8.366 | 17.150 | 12.938 | 14.706 | 5.278 |
| engineering | 32 | 0.974 | 0.956 | 0 | -0.272 | 2.759 | 50.746 | 3.340 | 20.728 | 16.353 | 12.500 | 2.526 |
| student | 31 | 0.996 | 0.975 | 0 | -0.049 | 0.910 | 17.391 | 2.207 | 37.587 | 36.371 | 9.677 | 1.761 |

Targets: new_grammar_errors = 0 · meaning_sim ≥ 0.80 per sentence (gate) · doc_sec_per_1000_words < 3 on the free CPU. sec_per_1000_words is per-paragraph requests (~70 words each), dominated by fixed per-request overhead.
