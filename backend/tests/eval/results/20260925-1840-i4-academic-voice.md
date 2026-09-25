# Humanize evaluation — 2026-09-25 18:40

intensity=4 · tone=academic · LanguageTool=on · LM=fallback

| group | paragraphs | meaning_sim | min_meaning_sim | new_grammar_errors | fk_grade_change | score_change | pct_sentences_changed | sec_per_1000_words | voice_match_before | voice_match_after | voice_match_improved_pct | doc_sec_per_1000_words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 34 | 0.979 | 0.909 | 0 | -0.573 | 1.168 | 47.794 | 4.371 | 17.150 | 19.400 | 82.353 | 3.178 |
| ai | 34 | 0.979 | 0.909 | 0 | -0.573 | 1.168 | 47.794 | 4.371 | 17.150 | 19.400 | 82.353 | 3.178 |

Targets: new_grammar_errors = 0 · meaning_sim ≥ 0.80 per sentence (gate) · doc_sec_per_1000_words < 3 on the free CPU. sec_per_1000_words is per-paragraph requests (~70 words each), dominated by fixed per-request overhead.
