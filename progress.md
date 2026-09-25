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
| P4 Walkthrough | done (awaiting review) |
| P5 Make it yours + Ownership | pending |
| P6 Prove it | pending |
| P7 Report Doctor | pending |
| P8 Export | pending |
| P9 Deck, Progress, Learn, Polish, Deploy | pending |

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

#### Next
- Review P4, then P5 (Make it yours + Ownership) as in CLAUDE.md §12.
- Tooling note: in Git Bash on this machine, heredocs piped into Python turned `\b`/`\1` into control characters; edit regex lines with the editor, not shell heredocs.
