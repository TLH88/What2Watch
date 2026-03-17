# Setup Guide

This guide is for the public self-hosted version of What2Watch.

## 1. Recommended Architecture

What2Watch is designed for a small, trusted environment such as a home server or LAN-accessible Docker host.

### Containers

- `frontend`
  - React + Vite UI
  - exposed on `http://localhost:3000`
- `backend`
  - FastAPI API
  - exposed on `http://localhost:8000`
- `db`
  - PostgreSQL 16
  - exposed on `localhost:5432`

### Data Flow

1. Users open the frontend in a browser.
2. The frontend sends API requests to the backend.
3. The backend stores app data in PostgreSQL.
4. The backend fetches metadata from TMDB.
5. Optional integrations:
   - Trakt for watch history and ratings
   - Jellyfin for local library availability
   - OpenAI, Anthropic, or Google AI for AI-assisted discovery

## 2. Before You Start

You need:

- Docker Desktop or Docker Engine with Compose
- a TMDB API key
- optionally:
  - a Trakt API application
  - a Jellyfin server and API key
  - an AI provider API key

## 3. Clone and Configure

1. Clone the repository.
2. Copy `.env.example` to `.env`.
3. Edit `.env`.

Minimum required values:

- `SECRET_KEY`
- `TMDB_API_KEY`

Recommended local defaults can stay unchanged:

- `DATABASE_URL`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

## 4. Start the Stack

Windows:

```powershell
.\scripts\start.bat
```

macOS/Linux:

```bash
./scripts/start.sh
```

Or:

```bash
docker compose up -d --build
```

The backend automatically runs Alembic migrations on startup.

## 5. Verify the App

Open:

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/api/docs`

Then:

1. Create an admin user in the app.
2. Open the admin screen.
3. Confirm TMDB is connected.

## 6. TMDB Setup

What2Watch uses TMDB as its main metadata source.

Steps:

1. Create a TMDB account.
2. Open the TMDB developer documentation and account API settings.
3. Request an API key.
4. Paste the key into `.env` as `TMDB_API_KEY`.
5. Restart the containers if they are already running.
6. In the app admin area, test TMDB connectivity.

Official TMDB getting started docs:

- https://developer.themoviedb.org/docs/getting-started

## 7. AI Provider Setup

AI is optional, but recommended if you want natural-language discovery and stronger explanation text.

Choose one provider in `.env`:

- `AI_PROVIDER=openai`
- `AI_PROVIDER=anthropic`
- `AI_PROVIDER=google`

Then set the matching key:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_AI_API_KEY`

### OpenAI

1. Create an OpenAI Platform account and project.
2. Create an API key.
3. Add it to `.env` as `OPENAI_API_KEY`.
4. Keep `AI_PROVIDER=openai`.

Official docs:

- https://platform.openai.com/docs/quickstart/step-2-set-up-your-api-key
- https://platform.openai.com/docs/guides/production-best-practices/model-overview

### Anthropic

1. Create an Anthropic Console account or workspace.
2. Generate an API key in account settings.
3. Add it to `.env` as `ANTHROPIC_API_KEY`.
4. Set `AI_PROVIDER=anthropic`.

Official docs:

- https://docs.anthropic.com/en/api/getting-started
- https://docs.anthropic.com/en/docs/quickstart

### Google AI

1. Create a Google AI Studio key.
2. Add it to `.env` as `GOOGLE_AI_API_KEY`.
3. Set `AI_PROVIDER=google`.

Official docs:

- https://ai.google.dev/gemini-api/docs/quickstart

## 8. Trakt Setup

Trakt is optional. It is used to import per-user watch history and ratings.

This app uses Trakt's device-code flow, so users authorize inside the app after the server-level client ID and secret are configured.

Steps:

1. Create a Trakt account.
2. Create a Trakt API application and obtain a client ID and client secret.
3. Add them to `.env`:
   - `TRAKT_CLIENT_ID`
   - `TRAKT_CLIENT_SECRET`
4. Restart the backend if needed.
5. In What2Watch, open a user profile and choose `Connect Trakt`.
6. Follow the device authorization flow shown in the UI.
7. Run ratings/history sync from the profile page or admin actions.

Official references:

- https://trakt.docs.apiary.io/
- https://trakt.tv/apps

## 9. Jellyfin Setup

Jellyfin is optional. It is used only to mark titles as locally available in your library.

Steps:

1. Install and configure Jellyfin.
2. Complete the Jellyfin setup wizard and add your movie/TV libraries.
3. Make sure your media has metadata/provider IDs where possible.
4. Create or copy a Jellyfin API key from your server admin settings.
5. Add the values to `.env`:
   - `JELLYFIN_URL`
     - example: `http://192.168.1.50:8096`
   - `JELLYFIN_API_KEY`
6. Restart the backend if needed.
7. In the What2Watch admin area, test the Jellyfin connection.
8. Run a Jellyfin sync to populate local availability flags.

Official Jellyfin docs:

- https://jellyfin.org/docs/general/quick-start/
- https://jellyfin.org/docs/general/post-install/setup-wizard
- https://jellyfin.org/docs/general/server/metadata/

## 10. Ongoing Operations

Useful commands:

```bash
docker compose up -d --build
docker compose down
docker compose logs -f
docker compose ps
```

To rebuild after changing environment variables:

```bash
docker compose down
docker compose up -d --build
```

## 11. Important Limitations

This repository is intended for self-hosted use in a trusted environment.

Current limitations:

- no authentication system
- permissive CORS configuration
- admin routes are not hardened for internet exposure
- Docker services run in developer-friendly mode
- API keys can be updated from the admin UI and are stored in local `.env`

Do not expose this stack directly to the public internet without adding:

- authentication and session handling
- stricter CORS and origin controls
- HTTPS and reverse proxying
- proper secret management
- production server configuration
