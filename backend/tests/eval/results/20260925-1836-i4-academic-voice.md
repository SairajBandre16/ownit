# Humanize evaluation — 2026-09-25 18:36

intensity=4 · tone=academic · LanguageTool=on · LM=fallback

| group | paragraphs | meaning_sim | min_meaning_sim | new_grammar_errors | fk_grade_change | score_change | pct_sentences_changed | sec_per_1000_words | voice_match_before | voice_match_after | voice_match_improved_pct | doc_sec_per_1000_words |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 97 | 0.989 | 0.922 | 0 | -0.240 | 1.125 | 29.006 | 3.956 | 24.862 | 24.954 | 34.021 | 4.330 |
| ai | 34 | 0.976 | 0.922 | 0 | -0.447 | 1.571 | 49.265 | 5.769 | 17.150 | 18.029 | 55.882 | 5.329 |
| engineering | 32 | 0.992 | 0.969 | 0 | -0.209 | 1.209 | 21.642 | 3.161 | 20.728 | 20.375 | 37.500 | 4.141 |
| student | 31 | 0.998 | 0.977 | 0 | -0.044 | 0.548 | 9.783 | 2.485 | 37.587 | 37.274 | 6.452 | 3.175 |

Targets: new_grammar_errors = 0 · meaning_sim ≥ 0.80 per sentence (gate) · doc_sec_per_1000_words < 3 on the free CPU. sec_per_1000_words is per-paragraph requests (~70 words each), dominated by fixed per-request overhead.
