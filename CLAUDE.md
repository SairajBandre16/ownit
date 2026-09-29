# OwnIt: Humanize it. Understand it. Own it.

> Build spec for Claude Code. Read this whole file before writing any code.
> ("OwnIt" is a working name; rename freely.)

---

## 0. Instructions for Claude Code (read first)

1. **Build phase by phase** (see §12). After each phase: run all tests, run the app, summarize what was built, and **stop and wait for my review** before starting the next phase.
2. **Hard constraint: no AI models, no external APIs.**
   - Do NOT add: `transformers`, `torch`, `tensorflow`, `sentence-transformers`, `openai`, `anthropic`, `ollama`, `langchain`, Hugging Face inference, or any hosted NLP API.
   - Allowed: classic NLP libraries and small local statistical pipelines (spaCy, NLTK/WordNet, KenLM n‑grams, word vectors, textstat, YAKE, sumy, LanguageTool self-hosted).
3. **No detector gaming.** Do not implement "AI detection probability" scores, detector-in-the-loop optimization, or any copy claiming the output bypasses Turnitin/GPTZero etc. The goal is natural, clear, *owned* writing.
4. Prefer small, pure, testable functions. Every analyzer and transform lives in its own module with its own unit tests.
5. All text spans use **character offsets** `[start, end)` into the exact string that was sent to the API.
6. I develop on **Windows**. Run the backend in **Docker (or WSL2)** because KenLM and LanguageTool (Java) are painful on native Windows. The frontend runs natively with Node.
7. Keep a `README.md` up to date with setup and run commands.
8. **No em dashes, anywhere** (UI copy, backend messages, code, comments, docs, commits). Use a comma, colon, full stop or brackets. Code that must match an em dash in user input writes the escape `\u2014`. `backend/tests/unit/test_no_em_dash.py` enforces this.

---

## 1. Vision

Engineering students have to write many essays, lab reports and project reports. Many generate a draft with AI, never read it, submit it, and then cannot answer a single viva question about it.

**OwnIt turns an AI draft into the student's own work in five steps:**

```
Paste / upload draft
   │
① HUMANIZE ─────── rule-based rewrite, every change explained, accept/reject each
   │
② WALKTHROUGH ──── paragraph-by-paragraph gist, glossary, simplify, concept map
   │
③ MAKE IT YOURS ── tool finds generic spots, student adds own examples, data, opinions
   │
④ PROVE IT ─────── quiz + Viva Simulator + teach-back
   │
⑤ EXPORT ───────── .docx + Understanding Report (unlocks after passing ④)
```

---

## 2. Unique factors (what no other humanizer does)

| # | Feature | One-liner |
|---|---|---|
| U1 | **Voice Fingerprint ("Write like me")** | Student pastes 1–3 samples of their *own* past writing. Stylometry builds their style profile, and the humanizer rewrites *toward their voice*, not a generic "human" voice. Shows a **Voice Match %**. |
| U2 | **Ownership Score + Ownership Heatmap** | Every character is tagged by origin (AI original / engine rewrite / student edit / student insertion). The editor can show a heatmap, and the student sees an honest "you wrote 38% of this" score. |
| U3 | **Viva Simulator** | Adaptive oral-exam practice. Questions are generated from the report, answers are graded by concept coverage, and follow-ups get harder or easier depending on the answer. Built for engineering vivas. |
| U4 | **Engineering Report Doctor** | Checks things generic tools ignore: SI unit formatting, unit consistency, abbreviations used before they're defined, figure/table numbering and references, tense per section, unsupported claims (claim–evidence check), and report structure. |
| U5 | **Understanding-gated export + Understanding Report** | Export unlocks after passing the understanding checks. The student also gets a revision sheet (their viva Q&A, glossary, weak concepts). |
| U6 | **Revision Deck (spaced repetition)** | Glossary terms, missed quiz items and the student's recurring writing mistakes become SM‑2 flashcards. |
| U7 | **Explainable by design + privacy-first** | Zero AI models, zero external APIs, and every change has a human-readable reason. Text isn't stored server-side (processing is stateless; local storage is the default). |

---

## 3. Tech stack

### Backend (Python 3.11)
| Purpose | Library |
|---|---|
| API | `fastapi`, `uvicorn[standard]`, `gunicorn`, `pydantic` v2 |
| NLP core | `spacy` + `en_core_web_md` (has word vectors) |
| Synonyms / WSD | `nltk` (WordNet, Lesk) |
| Inflection | `lemminflect` |
| Word frequency | `wordfreq` |
| Readability | `textstat` |
| Fluency LM | `kenlm` (5-gram ARPA/binary) with a pure-Python fallback (see §6.4) |
| Grammar | LanguageTool server (Docker image `erikvl87/languagetool`), called over HTTP |
| Keywords / summary | `yake`, `sumy` (TextRank), `networkx` |
| Files | `python-docx`, `pdfplumber` |
| Infra | `slowapi` (rate limits), `cachetools` (LRU by text hash), `orjson` |
| Testing | `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy` |

### Frontend
| Purpose | Library |
|---|---|
| Framework | Next.js (App Router) + TypeScript |
| Styling | Tailwind CSS + shadcn/ui |
| Motion | Framer Motion |
| Editor | TipTap (ProseMirror) with custom marks for highlights and ownership |
| Charts | Recharts |
| Concept map | `@xyflow/react` (React Flow) |
| State / data | Zustand (+ persist), TanStack Query |
| Local storage | IndexedDB via `idb-keyval` (documents, deck, history) |
| Testing | Vitest + Testing Library, Playwright (e2e smoke) |

### Hosting (free)
- Frontend: Vercel
- Backend + LanguageTool: one Docker image on Hugging Face Spaces (Docker SDK), or `docker-compose` locally
- Optional sync later: Supabase (Postgres + auth)

---

## 4. Repository structure

```
ownit/
├── PROJECT_SPEC.md
├── README.md
├── docker-compose.yml            # backend + languagetool
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── scripts/
│   │   ├── download_resources.py # spaCy model, NLTK data (wordnet, omw-1.4, punkt)
│   │   └── build_lm.py           # builds the n-gram LM from WikiText-103 (see §6.4)
│   ├── data/                     # gitignored: lm/, corpora/
│   ├── app/
│   │   ├── main.py  config.py  deps.py
│   │   ├── api/                  # routes_analyze.py, routes_humanize.py, routes_style.py,
│   │   │                         # routes_walkthrough.py, routes_personalize.py,
│   │   │                         # routes_assess.py, routes_doctor.py, routes_export.py
│   │   ├── schemas/              # pydantic models (mirror §8)
│   │   ├── core/
│   │   │   ├── nlp.py            # singletons: spaCy, KenLM, LanguageTool client, wordfreq
│   │   │   ├── segment.py        # paragraphs, sentences, section detection
│   │   │   ├── protect.py        # protected-span detection (§6.1)
│   │   │   └── spans.py          # offset utilities, span merging, diffing
│   │   ├── analyze/              # one module per metric (§5)
│   │   ├── humanize/
│   │   │   ├── pipeline.py
│   │   │   ├── transforms/       # one module per transform (§6.2)
│   │   │   └── ranking/          # fluency.py, meaning.py, grammar.py, style_fit.py, scorer.py
│   │   ├── style/                # fingerprint.py, delta.py (U1)
│   │   ├── walkthrough/          # gist.py, glossary.py, simplify.py, concept_map.py
│   │   ├── personalize/          # generic_detector.py
│   │   ├── assess/               # cloze.py, mcq.py, true_false.py, viva.py, teachback.py, grade.py
│   │   ├── doctor/               # units.py, abbreviations.py, figures.py, tense.py,
│   │   │                         # claims.py, structure.py (U4)
│   │   ├── export/               # docx_writer.py, understanding_report.py
│   │   └── resources/            # JSON lexicons and templates (§7)
│   └── tests/
│       ├── unit/                 # per analyzer/transform
│       ├── golden/               # input → expected output fixtures
│       └── eval/                 # evaluation harness (§11)
└── frontend/
    ├── app/
    │   ├── page.tsx                      # landing
    │   ├── workspace/page.tsx            # doc list
    │   ├── workspace/[docId]/page.tsx    # 5-step flow
    │   ├── voice/page.tsx                # Voice Fingerprint setup
    │   ├── viva/[docId]/page.tsx         # Viva Simulator
    │   ├── deck/page.tsx                 # Revision Deck
    │   ├── progress/page.tsx
    │   └── learn/[topic]/page.tsx
    ├── components/
    │   ├── editor/        # Editor.tsx, marks (issue, change, ownership, protected), HoverCard
    │   ├── steps/         # Stepper, HumanizeStep, WalkthroughStep, MakeItYoursStep, ProveItStep, ExportStep
    │   ├── analysis/      # ScoreGauge, SubScoreBars, SentenceRhythmChart, IssueList
    │   ├── diff/          # ChangeCard, DiffView, BulkActions
    │   ├── concept-map/
    │   ├── viva/
    │   └── ui/            # shadcn
    └── lib/
        ├── api.ts         # typed client (types generated from backend OpenAPI)
        ├── store.ts       # zustand stores
        ├── ownership.ts   # origin tracking + score (U2)
        ├── srs.ts         # SM-2 (U6)
        └── db.ts          # IndexedDB helpers
```

---

## 5. Analyze module (writing score)

`POST /analyze` returns an overall score from 0–100, five sub-scores, and a list of issue spans.

| Sub-score | Signals (all computed with spaCy/textstat/lexicons) |
|---|---|
| **Clarity** | Flesch–Kincaid grade vs target, % sentences > 30 words, nominalizations (`-tion/-ment/-ance` nouns + light verb "make/give/take/have"), wordy phrases |
| **Rhythm** | Std. dev. of sentence length (the "burstiness" of the text), variety of sentence openers (first-token POS + lemma distribution entropy), runs of 3+ similar-length sentences |
| **Vocabulary** | MTLD lexical diversity, repeated content lemmas within 2 sentences, stock/AI-style phrase density (lexicon), cliché density |
| **Voice** | Passive ratio (`nsubjpass`/`auxpass`), hedges ("might possibly", "it could be argued"), fillers ("very", "really", "basically"), weak verbs (is/has/does + noun) |
| **Correctness** | LanguageTool matches per 100 words (by category) |

Each sub-score is 0–100 and computed by mapping each metric through a piecewise-linear "good band" (define the bands in `analyze/bands.json` so they're tunable). Overall = weighted mean (Clarity .25, Rhythm .2, Vocabulary .2, Voice .2, Correctness .15).

Every issue has `{id, start, end, category, rule, severity: info|warn|error, message, suggestion?, lesson_slug}`.

---

## 6. Humanize engine

### 6.1 Protected spans (never modified)
Detect these and mark them as frozen:
- quotes (`"..."`, `“...”`)
- citations: `(Author, 2021)`, `(Author et al., 2021)`, `[3]`, `[3–5]`
- equations and LaTeX: `$...$`, `\(...\)`, lines containing `=` with math symbols
- numbers with units: `25 kN`, `3.3V`, `10^5 Pa`, `±0.2 mm`, percentages
- code: backtick spans, lines that look like code
- figure/table/equation references: `Fig. 3`, `Figure 2(a)`, `Table 1`, `Eq. (4)`
- abbreviations: all-caps tokens with 2–6 letters, plus `resources/eng_abbreviations.json`
- named entities (ORG, PERSON, GPE, PRODUCT, LAW, WORK_OF_ART)
- technical terms: top‑k YAKE keyphrases + noun chunks repeated ≥ 2 times
- the user's "keep these words" list

A transform may not touch any token that overlaps a protected span.

### 6.2 Transforms (each returns zero or more candidate sentences plus change records)
Each transform module exposes `apply(sent: Span, ctx: Context) -> list[Candidate]`, where `Candidate = {text, changes: [Change], transform_id}`.

1. **phrase_simplify.** Longest-match lookup in `wordy_phrases.json` + `ai_style_phrases.json` (e.g., "in order to"→"to", "due to the fact that"→"because", "it is important to note that"→∅, "delve into"→"examine", "a plethora of"→"many", "utilize"→"use"). Fix capitalization after deletions.
2. **synonym.** Only for content words (NOUN/VERB/ADJ/ADV) that aren't protected and aren't stopwords. Pick the WordNet sense via Lesk using sentence context; candidates = lemmas of that synset (+ direct hypernym lemmas for nouns, single-word only). Filters: same POS, wordfreq Zipf ≥ 3.5 and ≥ original Zipf − 0.5 (never make a word rarer), vector similarity ≥ 0.45 to the original in context. Re-inflect with lemminflect using the original tag. Cap at 15% of eligible words per sentence and never swap the same lemma twice in a paragraph.
3. **transition_vary.** Detect sentence-initial transitions (`transitions.json` groups them by function: addition, contrast, cause, result, example). If the same transition is used twice within 5 sentences, or the density is > 1 per 3 sentences, replace it with another from the same group or drop it.
4. **split_long.** For sentences > 28 words: split at a coordinating conjunction joining two independent clauses (`cc` whose head and conjunct both have their own subjects), or at a non-restrictive relative clause (", which …") by turning it into a new sentence ("This …").
5. **merge_short.** Two consecutive sentences, each < 9 words, sharing a subject lemma or linked by an obvious relation → join with ", and" / "; " / a subordinator.
6. **passive_to_active.** Only when an explicit agent exists (`agent` → `pobj`). Rebuild as agent + verb (conjugated to match the agent and original tense via lemminflect) + patient + remaining modifiers. **Skip in Methodology sections** (passive is conventional there).
7. **clause_front.** Move a trailing adverbial clause (`advcl` introduced by because/when/although/if/after) to the front, and vice versa, to vary sentence openers.
8. **opener_vary.** If ≥ 3 of the last 4 sentences start with the same POS/lemma (e.g., "The …", "This …"), try clause_front or a reordering of a fronted prepositional phrase.
9. **contractions.** Casual tone only.
10. **voice_fit (U1).** Nudge toward the student's fingerprint: adjust contraction rate, preferred transitions (use the student's own favorites), and sentence-length targets (feeds into ranking).

### 6.3 Ranking
For each sentence, generate candidates (original + single transforms + up to 2 chained transforms, max ~8), then score:

```
score = 0.35 * fluency_norm       # KenLM log-prob per token, normalized against the original
      + 0.30 * meaning_sim        # spaCy vector cosine + content-lemma overlap (F1), averaged
      + 0.15 * style_fit          # closeness to targets: tone + voice fingerprint (U1)
      - 0.20 * grammar_penalty    # new LanguageTool matches vs original (0 if none added)
```

**Hard gates (reject the candidate):** meaning_sim < 0.80, new grammar errors > 0, fluency drop > 15% vs original, touches a protected span.

The **intensity slider** (1–5) controls how many transforms are allowed and the minimum improvement required over the original. At intensity 1, only phrase_simplify and transition_vary run.

After choosing a candidate for each sentence, run a **document pass** that re-checks the sentence-length std. dev. and opener variety against targets and swaps in second-best candidates where that helps.

### 6.4 Fluency language model
- `scripts/build_lm.py` downloads WikiText-103 (raw text dataset; this is data, not a model API), normalizes it, and builds a 5-gram KenLM binary (`lmplz` + `build_binary`) inside Docker.
- Fallback (`ranking/fluency.py`): a pure-Python trigram model with stupid backoff, built from the same corpus into a pickled count table, for when KenLM isn't installed. Both implement the same `FluencyScorer` protocol.

### 6.5 Output
Every accepted edit produces a `Change` (see §8) with a `reason` written in plain English from a template in `resources/explanations.json`, keyed by transform + sub-rule, e.g.:
- `split_long`: "This sentence had {n} words. Splitting it at '{conj}' makes each idea easier to follow."
- `synonym`: "'{old}' → '{new}': a more common word with the same meaning here."

---

## 7. Resources (JSON lexicons)

Seed each file with the examples below, then **expand each to 300+ entries** with sensible, common-knowledge content. Keep them in versioned JSON so they can be reviewed.

- `wordy_phrases.json`: `{"in order to": "to", "due to the fact that": "because", "at this point in time": "now", "has the ability to": "can", "a large number of": "many", "with regard to": "about", "in the event that": "if", "prior to": "before", "is able to": "can", "make a decision": "decide", "conduct an analysis of": "analyze", "for the purpose of": "to"}`
- `ai_style_phrases.json`: each entry is `{phrase, replacement | null, note}`: "delve into", "in today's fast-paced world", "it is important to note that", "plays a crucial role", "a testament to", "navigate the complexities", "in the realm of", "seamlessly integrate", "ever-evolving landscape", "harness the power of", "a myriad of", "pave the way for", "unlock the potential", "in conclusion, it is evident that", "multifaceted"
- `cliches.json`, `fillers.json`, `hedges.json`, `weak_verbs.json`
- `transitions.json`: grouped by function
- `eng_abbreviations.json`: {abbr: expansion}: IoT, PLC, CNC, FEM, CAD, PCB, MOSFET, PWM, SCADA, HVAC, ADC, DAC, UART, RMS, …
- `si_units.json`: symbols, correct case, quantity type (length, mass, force, power, …)
- `generic_patterns.json`: patterns for the "Make it yours" detector (§9.3)
- `question_templates.json`: viva/quiz templates (§9.4)
- `explanations.json`: reason templates for every transform and issue
- `lessons/*.md`: short lessons (passive voice, concision, transitions, units, citing claims, …)

---

## 8. API contract (pydantic → OpenAPI → generated TS types)

```python
class Span(BaseModel): start: int; end: int
class Issue(Span): id: str; category: str; rule: str; severity: Literal["info","warn","error"]; message: str; suggestion: str | None; lesson_slug: str | None
class Change(BaseModel):
    id: str
    orig_start: int; orig_end: int          # offsets in input text
    new_start: int;  new_end: int           # offsets in output text
    original: str; replacement: str
    transform: str; category: Literal["clarity","rhythm","vocabulary","voice","grammar"]
    reason: str; confidence: float
class StyleProfile(BaseModel): features: dict[str, float]; function_word_freqs: dict[str, float]; sample_word_count: int
```

| Endpoint | Request | Response |
|---|---|---|
| `GET /health` | – | `{status, lm: "kenlm"\|"fallback", languagetool: bool}` |
| `POST /analyze` | `{text, target_grade?}` | `{score, subscores, issues[], stats{words,sentences,sentence_lengths[]}, sections[]}` |
| `POST /humanize` | `{text, tone: academic\|neutral\|casual, intensity: 1-5, keep_terms[], style_profile?}` | `{text, changes[], protected[], score_before, score_after, voice_match?}` |
| `POST /style/fingerprint` | `{samples: string[]}` (≥ 300 words total) | `StyleProfile` |
| `POST /style/compare` | `{text, profile}` | `{voice_match: 0-100, differences[] }` |
| `POST /walkthrough` | `{text}` | `{paragraphs[{span, gist, key_terms[{term, span, definition?}], simplified}], concept_map{nodes, edges}}` |
| `POST /personalize/spots` | `{text}` | `{spots[{span, pattern, prompt}]}` |
| `POST /assess/generate` | `{text, confusing_paragraphs[]}` | `{questions[{id, type: cloze\|mcq\|tf\|viva, prompt, options?, answer_key, source_span, concepts[]}]}` |
| `POST /assess/grade` | `{questions[], answers[]}` | `{results[{id, correct\|score, feedback, missed_concepts[]}], total}` |
| `POST /assess/viva/next` | `{text, history[{question, answer, score}]}` | `{question, difficulty, target_concepts[]}` |
| `POST /teachback` | `{text, explanation}` | `{coverage: 0-100, covered[], missed[], similarity}` |
| `POST /doctor` | `{text}` | `{issues[] (same Issue shape, category="engineering")}` |
| `POST /export/docx` | `{text, title, author?, understanding?}` | `.docx` file stream |
| `POST /export/report` | `{understanding data}` | `.docx` (Understanding Report) |
| `POST /files/extract` | multipart `.docx`/`.pdf` | `{text}` |

Limits: 3,000 words per request, 30 requests/min per IP, LRU cache keyed on `sha256(text + params)`.

---

## 9. Feature specs

### 9.1 Voice Fingerprint (U1)
Features, computed per 1,000 words where relevant:
- sentence length mean and std. dev., mean word length, MTLD
- relative frequencies of the top 60 English function words (for **Burrows' Delta**)
- punctuation per sentence: comma, semicolon, colon, dash, parentheses, question marks
- contraction rate, passive ratio, first-person pronoun rate
- transition preferences (which transitions they use, normalized)
- vocabulary tier distribution (wordfreq Zipf bins: <3, 3–4, 4–5, >5)
- sentence-opener POS distribution

`voice_match` = 100 × (1 − normalized distance), combining Burrows' Delta on function words (weight .5) with z-scored Euclidean distance on the other features (weight .5). Show the top 3 differences in plain words, e.g. "Your sentences are usually shorter (avg 16 vs 24 words)."

### 9.2 Ownership tracking (U2): frontend
- A TipTap mark `origin` with values `ai | engine | student_edit | student_insert` on every text range.
- Pasted text → `ai`. Accepted engine changes → `engine`. Typing inside an existing range → `student_edit`. Text inserted via "Make it yours" or typed in a new position → `student_insert`.
- Ownership Score (0–100) =
  `0.45 × (student chars / total chars)` + `0.20 × (decisions made / changes offered)` (accepting or rejecting a change both count) + `0.20 × understanding score` + `0.15 × personalization spots filled / spots found`.
- A heatmap toggle colors the text by origin. Show the formula breakdown in a popover. Be honest: never inflate the score.

### 9.3 Make it yours: generic-spot detector
Rules (in `generic_patterns.json`):
- vague quantifiers without numbers ("various", "numerous", "a wide range of", "significant" with no figure nearby)
- abstract claims with no example ("plays a crucial role in", "is widely used in", "has many applications")
- Results/Discussion sentences without a number or unit
- a Conclusion with no first-person or evaluative sentence
- 3+ consecutive sentences with no concrete noun (PROPN/NUM/unit)

Each spot gets a prompt, e.g.: "Name one specific application you've seen (lab, internship, project)." or "Add the value you measured, with its unit." The student's answer is inserted after the spot with origin `student_insert`.

### 9.4 Question generation (U3, U5)
- **Key sentences:** TextRank over sentences, plus all definition sentences (`X is/are (a|an|the) …`, `X refers to`, `X is defined as`).
- **Cloze:** blank the highest-scoring keyphrase in a key sentence; accept lemma matches and minor typos (Levenshtein ≤ 2 for words > 5 chars).
- **MCQ:** correct answer = the blanked term. Distractors = other keyphrases of the same entity/noun-chunk type from the text, then WordNet co-hyponyms (sister terms). Never use a distractor that appears in the same sentence.
- **True/False:** a true statement = key sentence. False versions by perturbation: swap two numbers or units, flip comparatives (increase↔decrease, higher↔lower, more↔less), swap two keyphrases, or negate the main verb.
- **Viva** (`question_templates.json`), templates matched against the dependency parse:
  - definition → "What is {X}?" / "Explain {X} in your own words."
  - causal markers (because / due to / therefore / as a result) → "Why {clause}?"
  - effect verbs (increase / reduce / affect / improve / cause) → "How does {subj} affect {obj}?"
  - method sentences in Methodology → "How did you {verb} {obj}?" / "Why did you choose {X}?"
  - results with numbers → "What does the value {num unit} tell you?"
  - comparisons → "What is the difference between {A} and {B}?"
- **Viva Simulator adaptivity:** difficulty ladder definition → how → why → compare/evaluate. Score ≥ 70 → move up a level on a new concept. Score < 40 → drop to the definition question for the concept they missed. Ten questions per session, optional 60 s timer per question.
- **Open-answer grading** (viva + teach-back): extract keyphrases/lemmas from the source span(s) as the expected concepts. Coverage = matched concepts / expected, matching by lemma, WordNet synonym, or vector similarity ≥ 0.7. Final score = 0.7 × coverage + 0.3 × vector similarity. Feedback lists the missed concepts and links to the source paragraph.

### 9.5 Engineering Report Doctor (U4)
- **Units:** missing space ("5kN" → "5 kN"), wrong case ("5 KG" → "5 kg", "kw" → "kW"), plural units ("5 kgs"), mixed systems for the same quantity type in one document, numbers without units in Results.
- **Abbreviations:** used before being defined as "Full Name (ABBR)"; defined twice; defined but never used.
- **Figures/tables:** every "Fig. n"/"Table n" is referenced in the text; numbering is sequential; captions are present (from .docx input).
- **Tense per section:** Methodology and Results are mainly past tense, Introduction/Theory mainly present tense (via spaCy `morph` Tense). Flag outlier sentences.
- **Claim–evidence:** sentences with strong-claim markers ("proves", "clearly shows", "significantly", "always", "best") and no citation, number or figure reference in the same or the next sentence → "Unsupported claim. Add evidence or soften it."
- **Structure:** detect headings; compare with a lab/project report template (Abstract, Introduction, Objectives, Theory, Methodology, Results, Discussion, Conclusion, References). Report missing or out-of-order sections and an abstract that is too long (> 250 words).

### 9.6 Revision Deck (U6)
- Cards come from: glossary terms (term → definition, preferably the student's own definition), missed quiz/viva items, and the student's top recurring writing issues (rule → example from their own text + fix).
- SM‑2 scheduling in `lib/srs.ts`, stored in IndexedDB. A daily review page with keyboard shortcuts (1–4 for grading).

### 9.7 Understanding gate + report (U5)
- Default gate: quiz ≥ 70% **and** teach-back coverage ≥ 60% **and** walkthrough ≥ 80% of paragraphs marked reviewed. It's configurable in settings (can be switched off, but is on by default).
- Understanding Report (.docx): title, date, Ownership Score breakdown, concepts mastered/weak, glossary, all viva questions with the student's answers and feedback, and a concept list for revision.

---

## 10. Frontend design

**Direction:** "a modern engineering notebook". An editorial feel with precise, technical details. Not a generic purple-gradient SaaS look.

- **Typography:** `Newsreader` (optical-size serif) for display headings and the editor text, `Schibsted Grotesk` for UI, `IBM Plex Mono` for numbers, scores and units. Avoid the stock "AI app" fonts (Inter, Instrument Serif, Fraunces, JetBrains Mono, Space Grotesk).
- **Colors (CSS variables, light + dark):**
  - light: paper `#F7F5F0`, ink `#1A1A1A`, muted `#6B6B6B`, rule lines `#E4E0D8`
  - dark: `#111214` bg, `#EDEBE6` text
  - one accent: signal orange `#FF5A1F` (focus, primary actions)
  - semantic highlights: clarity = amber, rhythm = sky, vocabulary = violet, voice = teal, grammar = red; ownership heatmap: ai = neutral gray, engine = blue, student_edit = green, student_insert = deep green
- **Layout:** the workspace is a 3-column layout on desktop (step rail | editor | insight panel) and stacks on mobile. A subtle grid-paper background pattern in the editor gutter.
- **Signature moments:**
  - animated score gauge that counts up from the before score to the after score after humanizing
  - diff cards that slide in, with ✓ / ✗ and keyboard shortcuts (J/K to move between cards, A to accept, R to reject)
  - an ownership heatmap toggle with a smooth color transition
  - the concept map zooms to the node for the paragraph being read
  - Viva Simulator in full-screen "exam hall" mode with a countdown ring
- **Landing page:** hero line "Humanize it. Understand it. Own it.", a live mini-demo (paste → changes with reasons), the 5 steps as a scroll story, a "0 AI models · 0 external APIs" badge, and an FAQ that states plainly that this is a learning tool.
- **Accessibility:** WCAG AA contrast, full keyboard navigation, and `prefers-reduced-motion` respected.

---

## 11. Quality, testing and evaluation

- **Unit tests** for every analyzer, transform, protector and question generator (≥ 5 cases each, including cases where it must *not* fire).
- **Golden tests** in `tests/golden/*.json`: `{input, params, must_contain[], must_not_change[], max_changes}`.
- **Protected-span invariant test:** fuzz random texts containing equations, units and citations → assert that they're byte-identical after humanizing.
- **Evaluation harness** (`tests/eval/run_eval.py`) on ~100 paragraphs (mix of AI-style drafts and real student-style text; include engineering reports). It reports: avg meaning_sim, new grammar errors (must be 0), readability change, writing-score change, % sentences changed, and runtime per 1,000 words (target < 3 s on the free CPU). Save results as a markdown table so runs can be compared.
- **Frontend:** component tests for the editor marks, ownership scoring and SM‑2, plus a Playwright smoke test of the full 5-step flow.
- CI: GitHub Actions runs ruff, mypy, pytest, and the frontend lint + tests.

---

## 12. Build phases (stop after each one for review)

| Phase | Scope | Acceptance criteria |
|---|---|---|
| **P0 Setup** | Monorepo, Docker Compose (backend + LanguageTool), `download_resources.py`, `/health`, Next.js + Tailwind + shadcn scaffold, design tokens, CI | `docker compose up` works; `/health` reports spaCy, LM mode and LanguageTool; the frontend shows the landing page skeleton |
| **P1 Analyze** | segment, protect, all §5 analyzers, `/analyze`; editor with issue highlights, hover cards, score gauge, sub-score bars, rhythm chart | Pasting text shows highlights; tests pass; protected spans are shown in a distinct style |
| **P2 Humanize v1** | phrase_simplify, synonym, transition_vary, split_long; LM build script + fallback; ranking + gates; `/humanize`; diff UI with accept/reject/bulk actions and before/after score | Eval harness runs; 0 new grammar errors; protected-span fuzz test passes |
| **P3 Humanize v2 + Voice** | passive_to_active, merge_short, clause_front, opener_vary, contractions, document pass; `/style/*`; Voice Fingerprint page; voice_fit in ranking; Voice Match % display | Voice Match increases after humanizing with a profile, on the eval set |
| **P4 Walkthrough** | gist, glossary, simplify, concept map, `/walkthrough`; Walkthrough step UI with "Got it / Confusing" | Each paragraph has a gist and key terms; the concept map renders and syncs with scrolling |
| **P5 Make it yours + Ownership** | generic-spot detector, `/personalize/spots`, insertion UI, TipTap origin marks, Ownership Score + heatmap | Origins are tracked correctly through edits and accepts; score breakdown shown |
| **P6 Prove it** | cloze/MCQ/TF/viva generation, grading, teach-back, Viva Simulator page | Questions are grammatical on the eval set (manual spot-check of 30); grading gives sensible feedback |
| **P7 Report Doctor** | all §9.5 checks, `/doctor`, engineering issue layer in the editor | Unit/abbreviation/figure/tense/claim tests pass |
| **P8 Export** | file upload (docx/pdf), `/export/docx`, Understanding Report, understanding gate | Exported .docx opens in Word with formatting intact; the gate enforces its thresholds |
| **P9 Deck, Progress, Learn, Polish, Deploy** | SM‑2 deck, progress dashboard (IndexedDB history), lessons, landing page polish, Dockerfile for HF Spaces, Vercel config | Deployed URLs work end-to-end; Lighthouse ≥ 90 for performance/accessibility on the landing page |

---

## 13. Known limits (keep honest in the UI copy)
- Rule-based rewriting is conservative; sometimes the best candidate is "no change". That's intended.
- passive_to_active and merge_short are the riskiest transforms, so keep their gates strict.
- WordNet has few technical terms, so the glossary asks the student to define unknown terms themselves (this is a feature: active recall).
- The app never claims to make text "undetectable". It helps students write clearly and understand and own their work.
