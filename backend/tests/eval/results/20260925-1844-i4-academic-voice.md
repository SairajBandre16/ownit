# Humanize evaluation: 2026-09-25 18:44

intensity=4 · tone=academic · LanguageTool=on · LM=fallback

| group | paragraphs | meaning_sim | min_meaning_sim | new_grammar_errors | fk_grade_change | score_change | pct_sentences_changed | sec_per_1000_words | voice_match_before | voice_match_after | voice_match_improved_pct | doc_sec_per_1000_words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 97 | 0.991 | 0.909 | 0 | -0.268 | 1.056 | 27.624 | 1.823 | 24.862 | 26.088 | 47.423 | 0.781 |
| ai | 34 | 0.979 | 0.909 | 0 | -0.573 | 1.168 | 47.794 | 2.873 | 17.150 | 19.400 | 82.353 | 1.053 |
| engineering | 32 | 0.996 | 0.980 | 0 | -0.159 | 1.575 | 20.149 | 1.331 | 20.728 | 21.822 | 43.750 | 0.813 |
| student | 31 | 0.999 | 0.988 | 0 | -0.045 | 0.397 | 8.696 | 1.017 | 37.587 | 37.826 | 12.903 | 0.349 |

Targets: new_grammar_errors = 0 · meaning_sim ≥ 0.80 per sentence (gate) · doc_sec_per_1000_words < 3 on the free CPU. sec_per_1000_words is per-paragraph requests (~70 words each), dominated by fixed per-request overhead.
