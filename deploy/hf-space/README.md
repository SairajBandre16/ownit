---
title: OwnIt API
emoji: 📓
colorFrom: gray
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# OwnIt API (Hugging Face Space)

The OwnIt backend (FastAPI, spaCy, WordNet, n-gram LM) and a LanguageTool server in one
container. No AI models, no external APIs at runtime; request text is processed in memory and
never stored.

## Deploying

1. Create a new Space with the **Docker** SDK (CPU basic is enough).
2. Copy into the Space repository (same paths as in this repo, so nothing needs editing):
   - this `README.md` → `README.md` at the Space root (the YAML header configures the Space),
   - `deploy/hf-space/Dockerfile` → `Dockerfile` at the Space root,
   - `deploy/hf-space/start.sh` → `deploy/hf-space/start.sh`,
   - the `backend/` folder **without** `backend/.venv`, `backend/data` and cache folders.
3. Push. The first build takes 15–20 minutes (it downloads LanguageTool and builds the
   fallback language model).
4. Check `https://<user>-<space>.hf.space/health`: it should report `"languagetool": true`
   and `"lm": "fallback"`.
5. Set the frontend's `NEXT_PUBLIC_API_URL` to the Space URL (see the main README). Browser
   requests from `*.vercel.app` are allowed by default; add other origins with the
   `OWNIT_CORS_ORIGINS` Space variable.

Optional Space variables: `WORKERS` (default 1), `LT_HEAP` (LanguageTool heap, default `1g`),
`OWNIT_RATE_LIMIT` (default `30/minute`).
