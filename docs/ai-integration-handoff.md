# What2Watch — AI Integration Handoff

This document captures the verified state of the project and decisions made during development, so a new conversation can pick up AI integration work without re-discovering what's already been built and tested.

---

## Project Summary

What2Watch is a locally-hosted household media discovery app. Users can discover new movies/TV shows and recall forgotten titles. It runs via Docker Compose on a Windows PC (LAN-only).

**Stack:** React + TypeScript + Tailwind CSS v4 (Vite) | FastAPI + Python 3.12 | PostgreSQL 16 (async) | Docker Compose

---

## Current State (All Phases Complete)

All 8 phases (0–7) are implemented, committed, and running:

| Phase | Status | What it covers |
|-------|--------|---------------|
| 0 | Done | Environment setup, Docker Compose, database |
| 1 | Done | Core data models, TMDB integration, title service |
| 2 | Done | User system, onboarding, preferences |
| 3 | Done | Discover flow (deterministic keyword-based) |
| 4 | Done | Title recall flow (deterministic clue extraction) |
| 5 | Done | Voice input via Web Speech API |
| 6 | Done | Feedback loop with pending rating reminders |
| 7 | Done | Admin dashboard, error handling, hardening |

---

## Verified Working Features

These have been tested in the running app:

- **User selection screen** — Choose from household profiles, create new users (max 5)
- **Discover flow** — Multi-strategy TMDB search with keyword parsing, person detection, genre/mood/era filters, weighted scoring
- **Title recall flow** — Clue extraction from free-text descriptions, multi-stage TMDB candidate search, narrowing questions
- **Voice input** — Browser-native Web Speech API on discover and recall pages
- **Pending rating reminders** — Auto-created after "watched" feedback, shown on home screen
- **Admin dashboard** — Source health, database stats, user management (edit/delete), sync actions
- **Error boundary** — React ErrorBoundary wraps the entire app
- **Global exception handler** — FastAPI catches unhandled errors with logging

---

## Verified Bug Fixes

These issues were encountered and resolved during development:

1. **Vite proxy in Docker** — `vite.config.ts` proxy target must use Docker service name (`http://backend:8000`), NOT `localhost`. Inside the frontend container, `localhost` refers to the container itself.

2. **TypeScript type-only exports** — Vite's transpiler strips `interface` exports. Any file importing a TypeScript interface must use `import type { Foo }` or `import { type Foo }` syntax, not bare `import { Foo }`.

3. **TMDB discover returning same results** — The original discover service used TMDB's `/discover/movie` endpoint with no filters when the user's query didn't match known genres. Fixed by implementing multi-strategy fetch: person-based discover, title text search, and structured discover — merged and deduped.

4. **Person name detection** — Added `resolve_person_names()` which searches TMDB's person API for 2-word keyword combinations (e.g., "tom cruise"), stores their person IDs, and uses the `with_cast` discover parameter.

5. **PendingRating rate endpoint** — The reminders rate endpoint originally called `fetch_and_store_title()` unnecessarily. Fixed to use `reminder.title_id` directly since PendingRating already stores it.

---

## AI Integration — Design Decisions Already Made

From `docs/media-discovery-app-design-plan-windows-rewritten.md`, Section 10:

### AI IS Allowed For:
- Interpreting free-text discovery requests (ambiguous queries)
- Extracting fuzzy title-recall clues from descriptions
- Generating the next clarifying question (smarter than hardcoded)
- Generating concise explanation text for recommendations

### AI is NOT Allowed For:
- Acting as the final recommendation engine by itself
- Inventing ratings or metadata
- Bypassing source-of-truth APIs (TMDB is canonical)
- Deciding final ranking without the scoring system
- Silently extending long-running searches

### Response Time Rules:
- Normal target: 15 seconds
- Soft ceiling: 20 seconds
- One-time extension: 25 seconds max

### Design Philosophy:
"AI used selectively, not as a crutch." Deterministic logic must work first; AI enhances it.

---

## AI Provider Configuration (Already Set Up)

`backend/app/core/config.py` has full provider abstraction:

```
ai_provider: str = "openai"  # openai | anthropic | google
openai_api_key: str = ""
anthropic_api_key: str = ""
google_ai_api_key: str = ""
```

Env vars in `.env.example`:
```
AI_PROVIDER=openai
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_AI_API_KEY=
```

**No AI libraries are installed yet.** `requirements.txt` has no openai/anthropic/google packages.

The directory `backend/app/services/ai/` exists with an empty `__init__.py`, ready for implementation.

---

## Where AI Should Be Integrated

### 1. Discover Service (`backend/app/services/discover_service.py`)

**Current:** `parse_query()` uses keyword matching for genres, moods, eras, runtime, quality, hidden gems. `resolve_person_names()` detects actors via TMDB person search. Clarifying questions are hardcoded.

**AI Enhancement Points:**
- **Query interpretation** — Use LLM to parse ambiguous queries like "something like Inception but funnier" into structured ParsedQuery fields. Fall back to keyword parsing if AI fails or is too slow.
- **Clarifying question generation** — Instead of 2 hardcoded questions (media type, genre/mood), use LLM to generate context-aware follow-ups.
- **Explanation text** — `build_explanation()` currently uses template strings. LLM could generate more natural "why you'd like this" text.

### 2. Recall Service (`backend/app/services/recall_service.py`)

**Current:** `extract_clues()` uses regex and keyword matching. `search_by_clues()` does multi-stage TMDB search. `get_narrowing_question()` is hardcoded (3 questions max).

**AI Enhancement Points:**
- **Clue extraction** — LLM would be much better at parsing "that movie where the guy wakes up on Mars and has to grow potatoes" into structured clues (setting: Mars, activity: farming, genre: sci-fi).
- **Narrowing questions** — LLM can ask smarter follow-ups based on the description and current candidate list.

### 3. New AI Service Module

Create `backend/app/services/ai/provider.py` with:
- Abstract base class for AI providers
- OpenAI, Anthropic, Google implementations
- Factory function that reads `settings.ai_provider`
- Shared prompt templates
- Timeout handling (15s target, 25s max)
- Graceful fallback to deterministic logic on failure

---

## Key Data Models (for AI prompt context)

### ParsedQuery (Pydantic)
```python
class ParsedQuery(BaseModel):
    media_type: str | None = None      # movie | tv
    genres: list[str] = []             # e.g. ["action", "sci-fi"]
    mood: str | None = None            # feel-good | dark | funny | scary | thought-provoking | exciting | relaxing | emotional
    era: str | None = None             # classic | 80s | 90s | 2000s | 2010s | recent | new | old
    runtime_pref: str | None = None    # short | long
    quality_pref: str | None = None    # high
    hidden_gem: bool = False
    keywords: list[str] = []           # leftover meaningful words
    person_ids: list[int] = []         # TMDB person IDs
    raw_query: str = ""
```

### Scoring Weights (in compute_score)
- Quality composite: 35%
- Genre/mood fit: 25%
- Freshness/diversity: 15%
- Local availability: 10%
- Hidden gem bonus: 10%
- Recency: 5%
- Keyword match bonus: up to +20
- Person match bonus: +15 per actor match

---

## File Locations

| Purpose | Path |
|---------|------|
| Design plan | `docs/media-discovery-app-design-plan-windows-rewritten.md` |
| Backend config | `backend/app/core/config.py` |
| Discover service | `backend/app/services/discover_service.py` |
| Recall service | `backend/app/services/recall_service.py` |
| Title service | `backend/app/services/title_service.py` |
| TMDB client | `backend/app/services/integrations/tmdb.py` |
| AI service dir | `backend/app/services/ai/` (empty, ready) |
| Discover schemas | `backend/app/schemas/discover.py` |
| User routes | `backend/app/api/routes/users.py` |
| Admin routes | `backend/app/api/routes/admin.py` |
| Reminder routes | `backend/app/api/routes/reminders.py` |
| Frontend app | `frontend/src/App.tsx` |
| Home page | `frontend/src/pages/Home.tsx` |
| Discover page | `frontend/src/pages/Discover.tsx` |
| Recall page | `frontend/src/pages/Recall.tsx` |
| Admin page | `frontend/src/pages/Admin.tsx` |
| User context | `frontend/src/context/UserContext.tsx` |
| Vite config | `frontend/vite.config.ts` |
| Docker Compose | `docker-compose.yml` |
| Requirements | `backend/requirements.txt` |
| Env template | `.env.example` |
| Start/stop scripts | `scripts/start.sh`, `scripts/start.bat`, etc. |

---

## Management Scripts

| Action | Bash | Windows |
|--------|------|---------|
| Start (builds) | `./scripts/start.sh` | `scripts\start.bat` |
| Stop | `./scripts/stop.sh` | `scripts\stop.bat` |
| Restart (rebuilds) | `./scripts/restart.sh` | `scripts\restart.bat` |

Docker Desktop must be running first. All scripts rebuild containers so code changes are picked up.

---

## Unstaged Changes

As of this writing, the following files have uncommitted changes that should be committed before starting AI work:

- `backend/app/services/discover_service.py` — Multi-strategy fetch, person detection, keyword/person scoring
- `backend/app/schemas/discover.py` — Added `person_ids` field to ParsedQuery
- `frontend/src/pages/Admin.tsx` — User management (edit/delete)
- `frontend/src/pages/ChooseUser.tsx` — Updates
- `frontend/src/context/UserContext.tsx` — Type import fix
- `frontend/index.html` — Updates
- `backend/app/api/routes/users.py` — PATCH/DELETE endpoints
- `scripts/` — New start/stop/restart scripts

---

## Git Info

- **Repo:** Local only (no remote push yet)
- **Branch:** master (main branch: main)
- **User:** TLH88 / myfreakingmial@gmail.com
- **Recent commits:** Phases 4–7 committed individually, plus a Vite proxy fix
