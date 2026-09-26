# OwnIt — Build Progress

Log of what has been built, phase by phase (see CLAUDE.md §12). Updated after each task.

## Environment decisions

- Machine: Windows 11, no Docker, no WSL. Backend runs **natively** in a Python 3.11 venv (`backend/.venv`, created with `uv`).
- LanguageTool 6.6 runs natively from `backend/data/languagetool` with the local Java 19 JDK (port 8010).
- KenLM does not build on native Windows without MSVC; the pure-Python trigram fallback LM is used locally. Docker files are still provided (backend + LanguageTool) for Linux / HF Spaces, where KenLM is built.
- Frontend: Next.js + TypeScript on Node 20.

## Phase status

| Phase | Status |
|---|---|
| P0 Setup | done |
| P1 Analyze | done |
| P2 Humanize v1 | done |
| P3 Humanize v2 + Voice | done |
| P4 Walkthrough | done |
| P5 Make it yours + Ownership | done |
| P6 Prove it | done |
| P7 Report Doctor | done |
| P8 Export | done |
| P9 Deck, Progress, Learn, Polish, Deploy | done (deployment itself pending the user's accounts) |

## Task log

- [x] Git repo initialised in `ownit/`.
- [x] Backend folder structure, `requirements.txt`, `requirements-dev.txt`, venv with all deps.
- [x] `scripts/download_resources.py` — spaCy `en_core_web_md`, NLTK (wordnet, omw-1.4, punkt, stopwords), optional LanguageTool zip. Ran successfully.
- [x] `/health` — reports spaCy model, LM mode (`kenlm`/`fallback`) + `lm_ready`, LanguageTool reachability.
- [x] `scripts/build_lm.py` — downloads WikiText-103 (parquet), normalises to 40M tokens, builds 5-gram KenLM when `lmplz` exists, always builds the numpy trigram fallback (`data/lm/trigram.npz`, 26 MB, 3.7M trigrams). Built locally.
- [x] `ranking/fluency.py` — `FluencyScorer` protocol, `KenLMScorer`, `TrigramScorer` (stupid backoff), `fluency_norm`, `fluency_drop`.
- [x] LanguageTool 6.6 client (`core/languagetool.py`) with LRU cache and graceful fallback when offline.
- [x] Next.js 16 + Tailwind v4 + shadcn/ui (base-ui) scaffold; design tokens (paper/ink/rule, signal orange, semantic highlight + ownership colours, light/dark); fonts Instrument Serif / Inter / JetBrains Mono.
- [x] Landing page skeleton: hero, mini demo, 5-step scroll story, "0 AI models · 0 external APIs" badge, FAQ.
- [x] Dockerfile (builds KenLM), `docker-compose.yml` (backend + LanguageTool), GitHub Actions CI, `scripts/dev.ps1` (native Windows run), README.
- [x] Verified: backend pytest 5/5, ruff + mypy clean; frontend tsc + eslint clean; `GET /health` → `{"lm":"fallback","lm_ready":true,"languagetool":true}`; landing page served on :3000.

### P1 Analyze
- [x] `core/segment.py` — paragraphs (blank-line blocks + heading lines), spaCy sentences with fragment re-joining ("Fig.", "et al."), canonical report sections (abstract … references) with numbered/markdown headings.
- [x] `core/spans.py` — half-open span utils, `SpanIndex`, `apply_edits`, word-level `diff_hunks`.
- [x] `core/protect.py` — quotes, citations (author-year + numeric), LaTeX/inline equations, numbers + units (from `si_units.json`), code spans/lines, Fig./Table/Eq. refs, URLs, abbreviations (caps + `eng_abbreviations.json`), named entities, YAKE keyphrases (noun phrases only) + repeated noun chunks, user keep-terms.
- [x] `core/lexicon.py` — phrase lexicon matcher with `{lemma}` inflection placeholders, context-aware verb tags/subject number, case matching.
- [x] Resources (each 300+ entries): `wordy_phrases`, `ai_style_phrases`, `cliches`, `fillers`, `hedges`, `weak_verbs`, `transitions`, `eng_abbreviations`, `si_units`; plus `explanations.json` (reason/message templates).
- [x] Analyzers: `clarity` (FK grade vs target, long sentences, nominalizations + WordNet verb suggestion, wordy phrases), `rhythm` (sentence-length SD, opener entropy, monotone runs, repeated openers), `vocabulary` (MTLD, near repeats, stock phrases, clichés), `voice` (passive with agent, Methodology exempt; hedges + stacked hedges; fillers; weak verbs; "There is … that"), `correctness` (LanguageTool, category-weighted). Tunable `analyze/bands.json`; weighted overall score; issue de-duplication.
- [x] `POST /analyze` → score, subscores, per-metric details, issues, stats, sections, protected spans. Warm latency ≈ 0.3 s for a 150-word text.
- [x] Backend tests: 81 passing (core, protect, each analyzer incl. must-not-fire cases, endpoint, word limit).
- [x] Frontend: typed API client (types generated from OpenAPI), IndexedDB doc store, Zustand workspace store, TipTap editor with `origin` mark, origin tracker, decoration layers (issues/protected/changes/spots/headings) + hover cards; ScoreGauge (count-up), SubScoreBars (metric breakdown), SentenceRhythmChart, IssueList with filters + "apply suggestion"; workspace doc list, new-doc dialog (paste/sample/upload), 5-step shell with step rail.
- [x] Frontend tests: 10 passing (offset mapping vs real editor, gate).

### P2 Humanize v1
- [x] Engine core: sentences are rewritten as non-overlapping *edits* on the original text (exact offsets + a reason per edit); chaining = union of edits (`humanize/types.py`, `edits.py` with minimal word-aligned edits and punctuation/capitalisation tidy-up).
- [x] Transforms: `phrase_simplify` (wordy/stock/filler/weak-verb lexicons, inflection, "for the purpose of measuring" → "to measure", a/an fixing), `synonym` (Lesk over top senses, sense-usage ranking, Zipf ≥ 3.5 and never rarer, reliable-vector filter, ≤15 %/sentence, once per lemma per paragraph; never swaps nouns — terminology stays exact), `transition_vary` (repeat within 5 sentences or density > 1/3 → same-group alternative or drop), `split_long` (> 28 words: independent-clause `cc` split, ", which …" → ". This …").
- [x] Ranking (`ranking/`): fluency via the n-gram LM comparing the *kept* tokens in old vs new context (saturated at p ≥ 0.1, noise-thresholded; whole-sentence mode for big rewrites), meaning = mean(vector cosine, content-lemma F1 with WordNet synonyms, ignoring words of removed empty phrases), style fit (cleanliness, length, tone, plainness, voice), batched LanguageTool grammar gate (errors near edits only, two rounds). Hard gates: meaning < 0.80, new grammar errors, fluency drop > 15 %, protected spans. Intensity controls transforms and the acceptance margin.
- [x] `POST /humanize` → text, changes (orig/new offsets, reason, confidence), protected spans, score before/after, stats.
- [x] Tests: transform units (incl. must-not-fire), gate tests, 25-seed protected-span fuzz test (byte-identical), 10 golden fixtures (`tests/golden/golden_cases.json`), endpoint tests. Backend total: 152 passing.
- [x] Eval harness `tests/eval/run_eval.py` + 97 paragraphs (AI drafts, student text, engineering report excerpts). Latest (intensity 3): **0 new grammar errors**, meaning_sim 0.971 (min 0.915), writing score +2.6 (+3.9 on AI drafts), 51 % sentences changed (76 % AI, 16 % student), **1.5 s per 1,000 words** in document mode. Results saved to `tests/eval/results/`.
- [x] Perf fixes: LanguageTool via 127.0.0.1 (Windows `localhost` IPv6 delay), grammar-check only top candidates, no re-parsing of candidates.
- [x] Frontend: humanize controls (tone, intensity 1–5, keep-terms, "write like me"), change cards that slide in with ✓/✗, J/K/A/R shortcuts, bulk accept/accept-confident/reject, pending changes shown in the editor (named decoration layers), accepted text tagged `engine` origin, decisions persisted and re-located after reload, animated before→after score gauge. Frontend tests: 20 passing.

### P3 Humanize v2 + Voice
- [x] Transforms: `passive_to_active` (explicit agent only; tense/aspect/modal/progressive/perfect handled; pronoun case; skips Methodology, negation, questions, relative clauses in the subject), `clause_front` (advcl because/when/if/after/… front ⇄ back), `opener_vary` (≥ 3 of last 4 openers the same → clause fronting or time/place PP fronting), `contractions` (casual: contract; academic: expand; neutral: follow the student's profile), `voice_fit` (student's favourite transition from the same group).
- [x] Document pass (`humanize/docpass.py`): `merge_short` (two < 9-word sentences sharing a subject / back-referencing pronoun / "However," / "So" → ", and" / "; however," / ", so"), rhythm and opener-variety swaps to gated runner-ups, all re-checked by one batched LanguageTool round.
- [x] Restructuring transforms may *move* protected text but never change it (every protected span in the window must reappear byte-identical); fuzz test still passes.
- [x] Intensity ladder: 1 gentle (phrases, transitions) → 2 (+synonyms, contractions) → 3 (+split long, opener variety, document pass) → 4–5 (+passive→active, clause fronting, merges).
- [x] Voice Fingerprint (`style/fingerprint.py`): sentence length mean/SD, word length, MTLD, punctuation per sentence, contractions, passive ratio, first person, transitions, Zipf tiers, opener POS mix, 60 function words. Reference stats for Burrows' Delta built from WikiText (`scripts/build_style_reference.py` → `resources/function_words.json`).
- [x] Voice Match (`style/delta.py`): 0.5 × Burrows' Delta + 0.5 × z-scored feature distance, with Bayesian shrinkage for short texts; top-3 differences in plain words. `POST /style/fingerprint` (≥ 300 words), `POST /style/compare`; `/humanize` returns `voice_match` before/after when a profile is sent.
- [x] Voice-aware ranking: `style/objective.py` keeps incremental document totals of parse-free fingerprint features, so each candidate is scored by how it moves the *whole document* towards the student's voice; plus a final voice-revert pass for low-value rewrites.
- [x] **Acceptance:** eval with a profile built from the student paragraphs, intensity 4 → Voice Match 24.9 → 26.1 overall (AI drafts 17.2 → 19.4, 82 % of AI paragraphs closer; engineering +1.1; student +0.2), 0 new grammar errors, meaning_sim 0.991.
- [x] Speed: string-based opener classes instead of re-parsing (intensity 4 at ~1.7 s / 1,000 words on the AI-draft document).
- [x] Frontend: `/voice` page (1–3 samples, word counter, build/rebuild/delete, fingerprint summary, "compare a text" with Voice Match meter + differences), live "Your voice" panel in the Humanize step with before → after.
- [x] Tests: backend 191 passing (P3: 39 new — every tense of passive→active, must-not-fire cases, clause/PP fronting, contractions by tone/profile, voice_fit, merges, fingerprint/compare/objective, style endpoints).

### P4 Walkthrough
- [x] Backend modules written: `walkthrough/gist.py` (TextRank central sentence + main-clause compression + stock-phrase condensing), `walkthrough/glossary.py` (definitions from the document, "Full Name (ABBR)", abbreviation list, WordNet for multi-word/rare terms; otherwise None for the student to define), `walkthrough/simplify.py` (one humanize pass at intensity 5 with `prefer="simplest"`, mapped back per paragraph, FK grade before/after), `walkthrough/concept_map.py` (noun keyphrases, co-occurrence edges labelled with linking verbs, pure-Python PageRank sizing, seeded spring layout), `walkthrough/service.py`, `schemas/walkthrough.py`, `POST /walkthrough` registered in `main.py`.
- [x] Shared helpers: `core/terms.py` (noun-phrase keyphrases that skip stock phrases, maths, citations, figure refs, generic single words), `core/graph.py` (PageRank without scipy). Humanize gained `prefer="simplest"`.
- [x] Manually checked on the sample draft: clean gists, sensible key terms/definitions, simplified paragraphs lower FK grade.

- [x] Quality pass on real drafts:
  - Gists keep figure refs and hyphenated words whole, drop parentheticals, keep noun coordination ("pH, TDS and hardness"), fall back to the full sentence rather than end on a function word or a cut list ("consist of", "tested at 7"), and skip heading fragments.
  - Glossary: "Full Name (ABBR)" trims leading words ("A programmable logic controller (PLC)"). Document definitions need the term to head its clause, use only "X is a/an …" (not "X is the best …") and match abbreviations case-sensitively ("IS 1498" is not the verb "is"). WordNet senses are chosen by gloss overlap with the paragraph (simplified Lesk); off-domain senses ("(tennis)") and unsupported ambiguous senses are rejected, so the student is asked to define the term instead.
  - Key terms grow to the whole noun compound ("capacitive soil moisture sensor", not "capacitive soil"); section names, unit symbols and evaluative pairs ("significant attention") are not terms; "simple to tune" is not a noun.
  - Concept map merges an abbreviation with its expansion, never labels edges with light verbs ("play", "have"), and spreads the layout by rank so labels don't clump.
  - A one-line title at the top is not a paragraph.
- [x] Fixes found on the way: clause_front produced "Because …, A controller was used" (`lower_first` now lower-cases the article "A"). `/walkthrough` is ~5× faster (per-document memo for the style/excluded span indexes, parse-free gloss lemmas): **2.3 s per 1,000 words** on a 2,035-word engineering document.
- [x] Backend tests: 26 new in `tests/unit/test_walkthrough.py` (gist incl. must-not-fire cases, abbreviation expansion, definition patterns, WordNet sense rejection, term offsets, unit/section filtering, offset mapping, concept map merge/determinism, title skipping, compound expansion, endpoint + word limit). Total: 217 passing; ruff + mypy clean. Eval harness rerun with LanguageTool on: 0 new grammar errors, meaning_sim 0.973 (unchanged).
- [x] Frontend Walkthrough step (`components/steps/WalkthroughStep.tsx`, `components/walkthrough/ParagraphCard.tsx`, `components/concept-map/ConceptMap.tsx`, `lib/walkthrough.ts`):
  - Builds automatically on first visit. Paragraph cards: section, serif one-line gist, text with key terms underlined, "Simplify" toggle with reading grade before → after, key terms with definition + source, "Define" / "In my words" for the student's own definition (stored in `walkthrough.ownDefs` for the Revision Deck).
  - Got it / Confusing per paragraph; keys J/K move, G got it (and advance), C confusing, S simpler version. Confusing paragraphs are listed in the insight panel (they feed step 4).
  - Understanding panel: % reviewed with the 80 % gate marker; `gate.ts` now counts marks only for paragraphs that exist.
  - React Flow concept map synced with scrolling: an IntersectionObserver picks the paragraph being read, and its concepts (plus their neighbours) are highlighted and zoomed to. Click a concept to jump to its paragraph; "Expand" opens the full map with all edge labels. Reduced motion respected.
  - Refresh after edits keeps marks on paragraphs whose text didn't change (`remapMarks`).
  - Workspace shell: fixed a 174 px horizontal overflow on phones (grid column `min-w-0`).
- [x] Frontend tests: 32 passing (new: `lib/walkthrough.test.ts`, `components/walkthrough/ParagraphCard.test.tsx`); eslint + tsc clean. Checked in Chromium via Playwright: desktop and 390 px mobile, marks persist after reload, no console errors.

- [x] Committed as `487abef`.

### P5 Make it yours + Ownership
- [x] `resources/generic_patterns.json` (≈ 480 entries): abstract claims, unnamed sources, benefits without figures, vague quantifiers, size words without figures, vague times, quantitative cues for Results, first-person/evaluative markers for the Conclusion, example markers; one label + prompt + answer starter per rule.
- [x] `personalize/generic_detector.py`: nine rules (§9.3): abstract_claim, vague_source, vague_benefit, results_no_number, vague_quantifier, vague_intensifier, vague_time, conclusion_no_voice, no_concrete_run. A phrase is only generic when the sentence (or, for claims/benefits/sizes/times, the next sentence) has no example, number, citation, name or dated year. Quotes, code, equations, headings and References are skipped. One spot per sentence (most specific rule wins), two per paragraph. Each spot has `insert_at` (end of its sentence) and a prompt that names the subject ("name one specific case of water scarcity …").
- [x] `POST /personalize/spots` → `{spots[{id, start, end, insert_at, pattern, label, prompt, starter, quote}]}` (cached, word limit).
- [x] Precision on the eval set: AI drafts 48 spots / 34 paragraphs, engineering excerpts 7 / 32, student-style text 1 / 31.
- [x] Backend tests: 59 new in `tests/unit/test_personalize.py` (≥ 5 fire and ≥ 5 must-not-fire cases per rule, selection caps, offsets, endpoint). Total: 276 passing; ruff + mypy clean.
- [x] Origin tracking (§9.2): pasted/dropped text from outside the editor is now `ai`; text copied inside the editor keeps its origin. New `components/editor/marks.test.ts` runs a real TipTap editor: paste → ai, typing inside AI or engine text → student_edit, typing after a finished sentence or in a new paragraph → student_insert, own text keeps its origin, accepted changes → engine, "Make it yours" answers → student_insert, deletions never create student text.
- [x] `lib/ownership.ts`: Ownership Score = 0.45 × student chars (non-whitespace) + 0.20 × decisions/offered (incl. earlier runs) + 0.20 × understanding (mean of walkthrough "Got it" share, quiz, teach-back) + 0.15 × spots filled/found. Honest by design: steps not done count 0; a part drops out (weights rescaled) only when its step ran and had nothing to offer; a deleted answer no longer counts as filled.
- [x] Make it yours step: spots highlighted in the editor (dashed) with hover prompts; spot cards with the prompt, a pre-filled answer box (Ctrl+Enter), Insert / Skip / "answer it after all"; answers are tidied into a sentence and inserted after the spot's sentence as `student_insert` via an invisible anchor decoration that maps through edits (fallback: re-locate by quote). "Check again" keeps filled spots. Spots are re-located after reloads/edits (`lib/personalize.ts`), stale ones say so.
- [x] Ownership panel: score, "you wrote N %", origin share bar + legend, heatmap toggle (smooth colour transition), per-part bars with points and details, "How it's calculated" popover with the formula. The workspace keeps `doc.ownership` in sync for the document list.
- [x] Frontend tests: 62 passing (new: ownership, personalize helpers, origin tracking, SpotCard); eslint + tsc clean. Checked in Chromium via Playwright: accept-all → engine chars, answered spot → student_insert chars and score 20 → 28, origins + filled spots persist after reload, no console errors, no horizontal overflow at 390 px.

- [x] Committed as `7748a74`.

### P6 Prove it
- [x] `resources/question_templates.json`: viva ladder (Define → Explain how → Explain why → Compare and evaluate), templates per kind, effect/choice verbs, causal markers, comparison markers, 60 true/false flip pairs.
- [x] `assess/keysent.py`: TextRank over sentence vectors + definition sentences ("X is a/an …", "X refers to …", "X is defined as …"); skips title/headings/References and cut-off fragments; strips stock openers ("Moreover, it is important to note that …") so questions are asked about the content; confusing-paragraph flag.
- [x] Generators: `cloze.py` (best keyphrase occurring once, outside citations/numbers; an abbreviation next to its expansion is blanked too), `mcq.py` (3 distractors of the same kind: abbreviation ↔ abbreviation, entity ↔ same entity, noun phrase ↔ similar length; most similar first, then WordNet sister terms; never from the question's sentence), `true_false.py` (flip direction/comparison words, swap numbers, negate the main verb with do-support, swap two terms as a last resort; a "false" statement never matches a document sentence), `viva.py` (definition/abbreviation, effect, method, choice, causal why-questions with do-support, result value, comparison, evaluate; article-, case- and number-aware concept naming; hedged, pronoun-subject and empty questions are skipped).
- [x] Viva Simulator adaptivity: score ≥ 70 → one level up on a new concept, < 40 → definition question for the missed concept, otherwise same level; 10 questions; never repeats. The bank is cached per document.
- [x] Grading (`grade.py`, `concepts.py`): cloze accepts lemma matches, typos (Levenshtein ≤ 2 on words > 5 letters) and abbreviation ↔ expansion; open answers score 0.7 × concept coverage (lemma, WordNet synonym, vector ≥ 0.7; multi-word concepts need their head) + 0.3 × similarity (content-word vectors, rescaled 0.60 → 0.90 so unrelated answers get 0); answers that mostly copy the source are capped at 50; feedback names the missed concepts.
- [x] Teach-back (`teachback.py`): expected concepts = the concept map's central concepts (as written in the body); similarity to a summary of the most central sentences; missed concepts come with the sentence where each appears.
- [x] Endpoints: `POST /assess/generate` (`seed` for a new quiz, confusing paragraph texts get extra questions), `POST /assess/grade`, `POST /assess/viva/next`, `POST /teachback`. Latency on a 2,035-word document: generate 1.9 s, teach-back 0.5 s, viva next < 0.1 s once the bank is built.
- [x] Segmentation fixes found on the way: "… shown in Fig. 7. It can be seen …" is two sentences again; "… 0.8 A. At light loads …" splits after a unit symbol.
- [x] Acceptance: 30-question spot-check on unseen eval paragraphs, first pass 27/30 grammatical, the three failures fixed and added as tests, second pass 30/30 (`tests/eval/results/questions-spotcheck.md`). Grading sanity: good viva answer 58-80+, vague 1-15, empty 0, copied capped at 50; good teach-back 82, vague 37.
- [x] Backend tests: 64 new in `tests/unit/test_assess.py` (definition detection, openers, cloze/MCQ/TF incl. must-not-fire cases, why-question conversion, every template generator, bank well-formedness, ladder up/down/stop/no-repeat, grading, teach-back, endpoints, word limit). Total: 339 passing; ruff + mypy clean.
- [x] Frontend Prove it step: tabs Quiz / Teach-back / Viva Simulator. Quiz: cloze with inline input, MCQ radio options, true/false; check answers → per-question result + feedback with the source sentence; pass mark vs the gate; Try again / New quiz; stale-text warning. Teach-back: explanation box with word count, coverage % vs gate, covered and missed concepts with the sentence to reread, copy warning. Insight panel: understanding gate (walkthrough/quiz/teach-back vs thresholds, switch to turn the gate off) + Ownership panel.
- [x] Viva Simulator page `/viva/[docId]`: full-screen dark "exam hall", difficulty ladder, big serif questions, optional 60-second countdown ring (auto-submits), Ctrl+Enter submit, "I don't know", feedback with score, covered/missed concepts and the sentence from the report, Enter for the next question, session summary (average, per level, concepts to revise). Sessions saved in IndexedDB (`assess.viva`, `assess.vivaHistory`).
- [x] Frontend tests: 74 passing (new: assess helpers, QuestionCard, a full VivaSimulator session with the API mocked incl. timer auto-submit); eslint + tsc clean.
- [ ] Not done: live browser check of the new screens. The dev servers were stopped by the system (low memory), and API types were generated from a dumped OpenAPI file instead of the running server.

- [x] Committed as `7694ab6`. From here the user asked to keep going phase after phase (commit each) until told to stop.

### P7 Report Doctor
- [x] `app/doctor/` — one module per §9.5 check, all issues `category="engineering"` with lesson slugs:
  - `units.py`: missing space ("12V" → "12 V"), wrong case ("5 KG" → "5 kg", "kw" → "kW"; ambiguous ones like "MW" are left alone), plural symbols ("2 hrs" → "2 h"), SI and non-SI units mixed for one quantity, Results/Discussion numbers with no unit (skips counts, ranges "120 to 410 Pa", years, figure numbers and dimensionless values such as COP or ratios). "45 in the test" is not inches.
  - `abbreviations.py`: used before "Full Name (ABBR)" (fix suggested from the later definition or the abbreviation list), defined twice (an Abstract definition may be repeated in the body), defined but never used; accepts "ABBR (Full Name)"; ignores common abbreviations, units, Roman numerals and tool names (MATLAB, LabVIEW, SolidWorks).
  - `figures.py`: first mentions must run 1, 2, 3; captions ("Figure 3: …", one per line) must be referred to; references to a missing caption; caption numbering gaps. With no captions at all (pasted text) only the order is checked.
  - `tense.py`: main-verb tense per sentence (auxiliary-aware); Methodology/Results expect past, Introduction/Theory present; outliers flagged, or one note when a whole section uses the other tense; references to the report ("Table 2 shows"), interpretation verbs and dated history are exempt.
  - `claims.py` + `resources/claim_markers.json` (50 markers): strong claims with no citation, number or figure/table reference in the same or the next sentence.
  - `structure.py`: missing core sections (Introduction, Methodology, Results, Conclusion; References as info), out-of-order sections, abstract > 250 words; "Results and Discussion" covers both; essays (< 2 recognised headings) are not checked.
- [x] `POST /doctor` → `{issues, counts}` (counts per check).
- [x] Fix found on the way: a title such as "Design of a Solar Tracker" was read as a Methodology heading (prefix match on "design"); a heading alias now only matches with a short tail that doesn't start with "of/for/a/the …".
- [x] Backend tests: 71 new in `tests/unit/test_doctor.py` (≥ 5 firing and ≥ 5 must-not-fire cases per check, service counts, endpoint). Total: 410 passing; ruff + mypy clean. On the eval texts the findings were real (undefined abbreviations in excerpts, out-of-order figure mentions, unsupported "clearly shows").
- [x] Frontend: step 1 has a third review tab, "Doctor", with a pass/count tile per check, the issue list filtered by check (IssueList gained `groupOf`), hover cards and one-click fixes for unit problems; a "Report Doctor" layer toggle shows the dashed engineering highlights in the editor at any time. `useDoctor` runs `/doctor` debounced.
- [x] Frontend tests: 78 passing (new: DoctorPanel); eslint + tsc clean. Live browser check still pending (dev servers stopped).

- [x] Committed as `57ceb0c`.

### P8 Export
- [x] `POST /files/extract` (`export/extract.py`): .docx paragraphs in order (headings, captions and list items kept, tables skipped with a warning); .pdf text layer with page numbers and running headers/footers removed, hyphenated line breaks re-joined, wrapped lines merged into paragraphs (a paragraph continues across a page break unless its sentence ended), headings by the segmenter's rule; scans (no text layer), broken files, other types and files over 10 MB are rejected with a clear message (422/415/413). The upload dialog shows the warnings.
- [x] `POST /export/docx` (`export/docx_writer.py`): Title + byline (author, date), Word headings from the segmenter (numbered "2.1" headings one level down), Caption style for figure/table captions, bullets for "- " lines, line breaks inside paragraphs kept, document properties set; optional ownership note. File name from the title.
- [x] `POST /export/report` (`export/understanding_report.py`): Understanding Report with Ownership Score breakdown (table), understanding checks (table), concepts mastered / to revise, glossary (student's own definitions first), every viva question with answer, score and feedback, quiz misses, teach-back, revision list.
- [x] Backend tests: 14 new in `tests/unit/test_export.py` (docx and hand-built PDF extraction incl. headers/page numbers/hyphenation, reflow across pages, errors, size limit; exported .docx re-opened with python-docx to check styles, headings, captions, bullets, properties and the ownership note; report sections and tables; endpoints). Total: 424 passing; ruff + mypy clean.
- [x] Frontend Export step: locked until the gate passes (lists what's missing with "Go there" links; the gate can be switched off in the panel); then title/author fields, optional ownership note, "Download .docx" and "Download Understanding Report" (report data built from the student's work in `lib/report.ts`: concepts mastered/weak ranked by how often they were missed, glossary with own definitions, quiz misses, viva turns); downloads recorded in `doc.exports` for the progress page.
- [x] Frontend tests: 85 passing (new: report builder, ExportStep gate lock/unlock and downloads); eslint + tsc clean.
- [ ] Not verified: opening the exported file in Microsoft Word itself (no Word on this machine); the structure and styles were checked by re-reading the file with python-docx.

- [x] Committed as `d4813e5`.

### P9 Deck, Progress, Learn, Polish, Deploy
- [x] Lessons: 24 Markdown lessons in `backend/app/resources/lessons/` (every `lesson_slug` an issue can link to, plus transitions, specific detail and viva preparation), grouped; `GET /lessons`, `GET /lessons/{slug}`. A test checks that every slug used in the code has a lesson.
- [x] Learn pages `/learn` and `/learn/[topic]`, rendered by a small Markdown renderer (`lib/markdown.tsx`) that builds React elements only (no raw HTML; only internal and https links).
- [x] SM-2 (`lib/srs.ts`): grades 1-4 → quality 1/3/4/5, Again = back in 10 minutes and a lapse, 1 d → 6 d → interval × ease, ease ≥ 1.3; interval preview labels; due cards; day streak in local time.
- [x] Revision Deck (`lib/deck.ts`, `/deck`): cards from glossary terms (own definitions first), missed quiz questions, viva answers under 70 and the student's recurring writing issues (example from their own text + fix; `doc.analysisText` now stored with the analysis); "Update from my documents" adds new cards without resetting schedules; review with Space / 1-4, interval preview on each button, stats (due, reviewed today, streak), card list with filters and delete. Links from the viva summary and the Export step.
- [x] Progress dashboard (`/progress`): tiles (documents, average ownership, checks passed, viva sessions, cards due, streak), per-document table (words, writing score first → latest, ownership, quiz, teach-back, viva average, status), viva-average line chart and 14-day review bar chart (Recharts; single series in `--chart-2`, validated with the dataviz palette checker in light and dark mode; hover tooltips; "Show as a table" for each chart).
- [x] Polish: skip-to-content link; footer links; home-link accessible name fixed; landing page no longer loads framer-motion (CSS scroll-driven reveal and tw-animate instead); header/footer links don't prefetch heavy routes (Recharts was being prefetched on the landing page).
- [x] Lighthouse (mobile, simulated throttling, production build, local): **performance 90, accessibility 100** on three runs (was 80-89 before the fixes; LCP 3.6 s is the remaining cost).
- [x] Deploy config: `deploy/hf-space/` (single-image Dockerfile with API + LanguageTool, `start.sh`, Space README with steps); Vercel instructions in the README; `frontend/.env.example`.
- [x] Playwright smoke test of the whole 5-step flow (`frontend/e2e/smoke.spec.ts`, `playwright.config.ts`).
- [x] `next build` passes (all 10 routes). Tests: backend 428 passing (4 new), frontend 103 passing (18 new: markdown, SM-2, deck, DeckReview, ProgressDashboard); ruff, mypy, eslint, tsc clean.
- [ ] Not done: the actual deployment (needs the user's Hugging Face and Vercel accounts), so "deployed URLs work end to end" is not verified; the Docker image wasn't built here (no Docker on this machine).
- [x] Committed as `da1e7bd`.

### Verification after P9
- [x] Playwright smoke test of the whole 5-step flow: **passes** against the production build (`next build` + `next start`, API with LanguageTool switched off to save memory), 13.4 s. (A first run passed against an orphaned `next dev` server from an earlier session that was still holding port 3000; it was stopped and the test re-run against the production build.)
- [x] Live pass over P6–P9 screens in Chromium (quiz, teach-back, Viva Simulator, Export gate, Deck, Progress, Learn, lesson): no console errors; no horizontal overflow at 390 px on any of them.
- Findings from the live pass, all fixed:
  - [x] Viva definition questions picked a weak source ("In conclusion, … the smart irrigation controller has the potential to revolutionize farming") and expected one concept ("farming"): a reasonable answer scored 13. Sources are now ranked (definition, then body sections over Conclusion/Abstract, then subject position, then centrality); a multi-word concept also uses body sentences about its head noun ("The controller was built around an ESP32 board."); a concept mentioned only in a summing-up sentence gets no definition question. The same answer now scores 38 ("partly there") and the feedback quotes the body sentence.
  - [x] After a weak answer the adaptive step could ask "Explain farming in your own words."; it now uses the same "definable" filter as the question bank.
  - [x] The washed-out viva feedback screenshot was only the fade-in; settled, contrast is fine.
  - [x] 4 regression tests (backend total 432).

#### Next
- Deploy (needs the user's Hugging Face and Vercel accounts).
- Tooling note: in Git Bash on this machine, heredocs piped into Python turned `\b`/`\1` into control characters; edit regex lines with the editor, not shell heredocs.
