# OwnIt desktop app

Wraps the OwnIt frontend and backend into one downloadable app. No AI models
and no external APIs, same as the website: the backend runs locally on the
user's own machine, in Docker.

## How it works

1. On launch, Electron checks Docker is installed and running.
2. It runs `docker compose pull` then `up -d` against `docker-compose.desktop.yml`,
   which points at prebuilt images on GHCR (`ghcr.io/sairajbandre16/ownit-backend`
   and the public `erikvl87/languagetool` image). Pulling on every launch is
   how a backend update reaches every installed copy: push a change to
   `backend/`, CI rebuilds and republishes the `:latest` image, and users get
   it the next time they open the app.
3. It starts the Next.js frontend as a standalone Node server (bundled with
   the app, so users never need Node) and loads it in the main window.
4. `electron-updater` checks GitHub Releases for a newer app version and
   installs it automatically. This covers the app shell itself (frontend
   code, Electron version), separate from the backend image above.

## One-time setup before the first release

The backend image and the GitHub Releases both need to be reachable
**without a login** for anonymous `docker pull` and for `electron-updater` to
work on a private repo:

1. Push to `main` once so `.github/workflows/backend-image.yml` publishes the
   first `ownit-backend` image, then go to the package's GitHub page
   (Settings) and set its visibility to **Public**.
2. Either make the `ownit` repo public, or keep it private and know that
   auto-update and anonymous image pulls will not work until it is. There is
   no supported way to give end users an update token safely.

## Local dev

```powershell
cd desktop
npm install
npm start          # builds the frontend standalone bundle, then launches Electron
```

Requires Docker Desktop running locally (same as `docker compose up` for the
web version).

## Building installers

```powershell
cd desktop
npm run dist        # unsigned local build, no publish
```

## Releasing

```powershell
git tag v0.2.0
git push origin v0.2.0
```

`.github/workflows/release.yml` builds Windows/macOS/Linux installers and
publishes them as a GitHub Release. Every running copy of OwnIt checks this
on launch and updates itself.
