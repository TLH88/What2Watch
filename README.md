# What2Watch

What2Watch is a self-hosted movie and TV recommendation app for households. It combines TMDB metadata, optional Trakt history, optional Jellyfin library matching, and an AI provider to help users discover something to watch or recall a title from vague clues.

This repository is source-available under the PolyForm Noncommercial 1.0.0 license.

## Intended Use

This project is designed for self-hosted use on a trusted local network or private server. It is not production-hardened for direct public internet exposure. You could easily host it on Vercel or similar and have access to it anytime without the local network connection requirement. 

## License

This project is licensed under PolyForm Noncommercial 1.0.0.

You may use, study, and modify this project for personal and other noncommercial purposes.

Commercial use, monetization, resale, paid hosting, bundling into paid products, or other revenue-generating use is not permitted without prior written approval from the developer.

See `LICENSE` for the exact terms.

## Stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL 16
- Integrations: TMDB, Trakt, Jellyfin
- AI providers: OpenAI, Anthropic, or Google AI
- Local deployment: Docker Compose

## Quick Start

### 1. Prerequisites

- Docker Desktop with Docker Compose enabled
- A TMDB API key
- An API key for OpenAI, Anthropic, or Google AI
- Optional (highly recommended): Trakt client ID and secret
- Optional: Jellyfin base URL and API key


For a full architecture and integration walkthrough, see `docs/setup-guide.md`.

### 2. Configure environment

Copy the sample environment file:

```powershell
Copy-Item .env.example .env
```

or on macOS/Linux:

```bash
cp .env.example .env
```

Then update `.env` with your own values. (This can be done within the app if you want a UI for input)

Required for the core app:

- `SECRET_KEY`
- `TMDB_API_KEY`

Required if you want AI-powered recommendations:

- `AI_PROVIDER`
- The matching provider key for that provider (this can be chagned at any time, suggest using an older model for cost savings)

Optional integrations:

- `TRAKT_CLIENT_ID`
- `TRAKT_CLIENT_SECRET`
- `JELLYFIN_URL`
- `JELLYFIN_API_KEY`

### 3. Start the app

Windows:

```powershell
.\scripts\start.bat
```

macOS/Linux:

```bash
./scripts/start.sh
```

Or directly with Docker:

```bash
docker compose up -d --build
```

The backend container applies Alembic migrations automatically on startup.

### 4. Open the app

- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8000/api/docs`

## First-Time Setup

1. Open the app and create at least one user.
2. In the admin area, verify TMDB connectivity.
3. If using AI recommendations, add your provider key and select the active provider.
4. If using Jellyfin or Trakt, configure those integrations and run a sync from the admin or profile pages.

## Third-Party Connections

What2Watch can run with TMDB only, but the full feature set depends on four external systems:

- TMDB
  - required
  - used for core movie and TV metadata
- AI provider
  - used for AI-assisted discovery and title recall
- Trakt
  - optional (highly recommended for full functionality)
  - used for importing ratings and watch history
- Jellyfin
  - optional
  - used for marking titles as available in your local library

Step-by-step setup instructions for all of these are in `docs/setup-guide.md`.

## Screenshots

<p align="center">
  <img src="docs/screenshots/0.%20What2Watch_Home.png" width="30%" alt="User selection screen" />
  <img src="docs/screenshots/1.%20What2Watch_Main.png" width="30%" alt="Home screen top section" />
  <img src="docs/screenshots/2.%20What2Watch_MainLower.png" width="30%" alt="Home screen lower section" />
</p>

<p align="center">
  <img src="docs/screenshots/3.%20What2Watch_MainBottom.jpg" width="30%" alt="Home screen bottom section" />
  <img src="docs/screenshots/4.%20What2Watch_MovieSearch.jpg" width="30%" alt="Movie search screen" />
  <img src="docs/screenshots/5.%20What2Watch_MovieRecommendations.jpg" width="30%" alt="Recommendation results" />
</p>

<p align="center">
  <img src="docs/screenshots/6.%20What2Watch_HiddenGem-Curveball.jpg" width="30%" alt="Hidden gem and curveball results" />
</p>

- User selection screen for shared household profiles
- Home screen with featured discovery entry points
- Home screen continuation with TV and group-watch actions
- Home screen bottom section with title recall, watchlist, and recent activity
- Search flow with free-text input, genre chips, and voice entry
- Ranked recommendation results with explanations, feedback actions, save/watch controls, and trailer access
- Collection-aware results showing hidden gem and curveball recommendations

## Environment Variables

The main variables are documented in `.env.example`.

Notes:

- `DATABASE_URL` targets the Docker Postgres service by default and should work unchanged for local Compose usage.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` can be left at their defaults for local development.
- `SECRET_KEY` should be replaced with a long random string before any real deployment.

## Repo Hygiene

Before pushing to GitHub, make sure you do not commit:

- `.env`
- `certs/`
- `logs/`
- `backups/`
- any exported database dumps or screenshots containing personal data

This repo's `.gitignore` is configured to exclude those paths.

## Useful Commands

```bash
docker compose up -d --build
docker compose down
docker compose logs -f
```

## Notes for Public Deployment

- The current Docker setup is optimized for local/self-hosted use.
- CORS is permissive by default (`["*"]`), which is convenient for home use but should be tightened for internet-facing deployments.
- The backend stores admin-updated API keys in the local `.env` file. Treat that file as sensitive.
- HTTPS, authentication hardening, secret management, and reverse proxy setup should be added before exposing this app publicly on the internet.

## Repository Files

- `LICENSE`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `docs/README.md`
- `docs/setup-guide.md`
