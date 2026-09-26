# OwnIt — Humanize it. Understand it. Own it.

OwnIt turns an AI-written draft into a student's own work in five steps: **Humanize → Walkthrough → Make it yours → Prove it → Export**. Everything is rule-based and explainable: no AI models and no external APIs. The full build spec is in [`CLAUDE.md`](CLAUDE.md); build progress is in [`progress.md`](progress.md).

## What's in it

| Where | What |
|---|---|
| `/workspace/[id]` step 1 · Humanize | writing score, suggestions, explained rewrites (accept/reject), Report Doctor (units, abbreviations, figures, tense, claims, structure) |
| step 2 · Walkthrough | one-line gist, key terms and glossary, simpler version, concept map synced with scrolling |
| step 3 · Make it yours | generic spots with prompts; answers inserted as your own text; Ownership Score + heatmap |
| step 4 · Prove it | quiz (cloze, multiple choice, true/false), teach-back, Viva Simulator (`/viva/[id]`) |
| step 5 · Export | `.docx` and the Understanding Report, unlocked by the understanding gate |
| `/voice` | Voice Fingerprint from your own past writing |
| `/deck` | Revision Deck: SM-2 flashcards from your glossary, missed questions and common writing issues |
| `/progress` | per-document scores, viva history, review activity |
| `/learn` | short lessons linked from every suggestion |

## Stack

- **Backend** — Python 3.11, FastAPI, spaCy (`en_core_web_md`), NLTK/WordNet, lemminflect, wordfreq, textstat, YAKE, sumy, a trigram/KenLM fluency model, and a self-hosted LanguageTool server.
- **Frontend** — Next.js 16 (App Router) + TypeScript, Tailwind v4 + shadcn/ui, TipTap, Framer Motion, Recharts, React Flow, Zustand, TanStack Query, IndexedDB.

## Quick start (Windows, no Docker)

Prerequisites: Python 3.11 (or [`uv`](https://docs.astral.sh/uv/)), Node 20.9+, Java 17+.

```powershell
# 1. Backend environment
cd backend
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt -r requirements-build.txt
.venv\Scripts\python scripts\download_resources.py --languagetool   # spaCy model, NLTK data, LanguageTool
.venv\Scripts\python scripts\build_lm.py --skip-kenlm                # fallback trigram LM (~10 min, ~300 MB download)

# 2. Frontend
cd ..\frontend
npm install

# 3. Run everything (opens three windows: LanguageTool :8010, API :8000, web :3000)
cd ..
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

Open http://localhost:3000. API docs are at http://localhost:8000/docs.

### Running services individually

```powershell
# LanguageTool
cd backend\data\languagetool\LanguageTool-6.6
java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8010 --allow-origin "*"

# API
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# Web
cd frontend
npm run dev
```

## Docker (Linux / WSL2 / Hugging Face Spaces)

```bash
docker compose up --build          # backend :8000 + LanguageTool :8010
# build the 5-gram KenLM model inside the container (optional, ~30 min):
docker compose run --rm backend python scripts/build_lm.py
```

The Docker image compiles KenLM, so `/health` reports `"lm": "kenlm"` once `data/lm/wiki5.binary` exists. Without it, the pure-Python trigram fallback is used (`"lm": "fallback"`).

## Deploying (free)

The website goes on **Vercel** (free, no card). The backend needs ~2.5 GB of memory (spaCy, the LM and LanguageTool), which free app hosts don't offer, so the free way is to **run it on your own PC and share it through a Cloudflare quick tunnel** (free, no account, no card).

### 1. Website → Vercel

Push the repository to GitHub, import it in Vercel with **Root Directory** `frontend`, and deploy. `NEXT_PUBLIC_API_URL` is optional: visitors connect to your PC through a share link (below), and anyone can pick a server from **Server** in the top bar.

### 2. Backend → your PC + Cloudflare Tunnel

```powershell
powershell -ExecutionPolicy Bypass -File scripts\share.ps1 -Site https://<your-app>.vercel.app
```

The script downloads `cloudflared` once, starts LanguageTool and the API if they aren't running, opens a tunnel and prints:

```
OwnIt is shared at:  https://<random-words>.trycloudflare.com
Share this link:     https://<your-app>.vercel.app/?api=https%3A%2F%2F<random-words>.trycloudflare.com
```

Open or send the share link. The website asks the visitor to confirm the server once, then remembers it. The tunnel address is new every time you run the script, so send a fresh link each session. Press **Ctrl+C** to stop sharing (only what the script started is stopped). Options: `-NoGrammar` (skip LanguageTool, saves ~1 GB of memory), `-Minutes 60` (stop automatically). Your PC must stay on and awake while people use it. Rate limits apply per visitor (the API reads Cloudflare's visitor address, trusted only from the local tunnel). Logs go to `backend/data/share-logs/`.

### Other hosts

`deploy/hf-space/` has a single-image `Dockerfile` (API + LanguageTool, fallback LM built at image build time) and a `start.sh` that serves on `$PORT` (default 7860). It runs on any Docker host: an Oracle Cloud Always Free VM, Google Cloud Run, or a Hugging Face Docker Space (Hugging Face now requires a paid plan for Docker Spaces). Test the image locally with:

```bash
docker build -f deploy/hf-space/Dockerfile -t ownit-space .
docker run -p 7860:7860 ownit-space       # then open http://localhost:7860/health
```

With a permanent backend address, set `NEXT_PUBLIC_API_URL` in Vercel to it and redeploy. The API accepts requests from `*.vercel.app`; for a custom website domain, add it to `OWNIT_CORS_ORIGINS`. See `frontend/.env.example`.

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `OWNIT_LANGUAGETOOL_URL` | `http://localhost:8010` | LanguageTool server |
| `OWNIT_LANGUAGETOOL` | `1` | Set `0` to disable grammar checks |
| `OWNIT_MAX_WORDS` | `3000` | Words per request |
| `OWNIT_RATE_LIMIT` | `30/minute` | Per-IP rate limit |
| `OWNIT_CORS_ORIGINS` | `http://localhost:3000,...` | Allowed browser origins |
| `NEXT_PUBLIC_API_URL` (frontend) | `http://127.0.0.1:8000` | Backend URL |

## Tests and checks

```powershell
cd backend
.venv\Scripts\python -m pytest -q          # unit + golden + fuzz tests
.venv\Scripts\ruff check . ; .venv\Scripts\mypy app
.venv\Scripts\python tests\eval\run_eval.py   # evaluation harness -> tests/eval/results/

cd ..\frontend
npm test            # Vitest
npm run lint
npm run e2e         # Playwright smoke test of the 5-step flow (needs the stack running; npx playwright install chromium once)
npm run gen:api     # regenerate lib/api-types.ts from the running backend's OpenAPI
```

Tests that need LanguageTool or the LM skip themselves if those aren't available.

## Privacy

The API is stateless: request text is processed in memory (with a short in-process LRU cache) and never written to disk. Documents, the revision deck and history live in the browser's IndexedDB.

## Honest limits

Rule-based rewriting is conservative, so sometimes the best candidate is "no change". WordNet knows few technical terms, so the glossary asks you to define unknown terms yourself. OwnIt never claims to make text "undetectable" — it helps you write clearly and understand and own your work.
