# Media Discovery App - Windows-Hosted Design and Implementation Plan

This is the fully revised execution blueprint for the local household media discovery app.

It is tailored to this deployment model:
- Windows-based home PC as the primary application host
- LAN-only access for end users
- React + Tailwind frontend
- FastAPI backend
- PostgreSQL database
- Docker Desktop + Docker Compose on Windows
- NAS used for storage, Jellyfin, and optional backups
- TMDB + Trakt + Jellyfin/NAS data strategy
- Optional trailers
- Hybrid AI used only where it adds value

## 1. Project Intent

### Goal
Build a local web app that helps household users:
- discover movies and TV shows based on preferences, constraints, and context
- identify a movie or TV show they remember but cannot name
- improve recommendations over time through feedback and watch history

### Product principles
- Mobile-first
- Dark theme by default
- Dead simple to use
- Quick to respond
- AI used selectively, not as a crutch
- Recommendations must be explainable
- User preference data must remain separated by profile
- The stack must be easy to develop, deploy, and maintain on a Windows PC
- The NAS should remain a media/storage dependency, not the compute host

## 2. Host Environment Baseline

### Primary host
**Windows PC**
- ASUS ROG NUC
- Intel Core Ultra 9
- Nvidia GeForce RTX 5070 mobile GPU
- 32 GB DDR5 RAM
- 1 TB NVMe

### Secondary infrastructure
**NAS**
- stores media files
- hosts Jellyfin and media libraries
- may store backups of database dumps and app backups
- may expose local metadata or `.nfo` information where useful

### Why this deployment model is the right one
The Windows PC gives you far more CPU, memory, and storage performance than the NAS. That means:
- easier Docker deployment
- better local development workflow
- lower risk of resource starvation
- room for background sync jobs and metadata caching
- room for future local AI experiments if you want them later

The NAS stays focused on storage and media-serving responsibilities.

## 3. Official v1 Scope

### Included in v1
- User picker landing screen
- Up to 4 local user profiles
- One admin profile
- Discover mode
- Remember-a-title mode
- Typed input
- Voice input
- Adaptive follow-up questions
- 3 to 5 ranked recommendation results
- Hidden gem / outlier slot
- Trakt import
- Manual onboarding
- In-app thumbs up/down
- Save for later / watched / already seen actions
- Admin settings for source integrations and sync
- LAN-only access from phones, tablets, and computers on the home network

### Explicitly deferred to v2
- Spoken assistant responses by default
- Push notifications as a primary workflow
- Remote access outside the home network
- Deep streaming-provider account integrations
- Always-listening voice
- Voice-based user identification
- Advanced household preference negotiation engine
- Full analytics dashboard
- Local model hosting unless it becomes strategically useful after v1

## 4. Technology Stack

### Frontend
- React
- Tailwind CSS

### Backend
- FastAPI
- Python 3.12+

### Database
- PostgreSQL

### Background jobs
- lightweight Python scheduler or worker
- APScheduler is sufficient initially
- avoid queue infrastructure unless it becomes necessary later

### Deployment/runtime
- Docker Desktop on Windows
- WSL2 enabled
- Docker Compose for local orchestration

### Integrations
- TMDB API
- Trakt API
- Jellyfin API
- AI provider API
- STT provider API
- Optional YouTube trailer fallback only when needed

## 5. Data Source Strategy

### TMDB
Primary canonical metadata source for:
- title identity
- synopsis
- genres
- people/cast/directors
- release dates
- runtimes
- videos if available
- watch-provider metadata when useful

**Rule:** TMDB ID is the canonical title spine.

### Trakt
Primary source for:
- watched history
- ratings history
- lists
- personal preference bootstrap

### Jellyfin / NAS
Primary source for:
- local media availability
- local file/library presence
- local metadata reconciliation when useful

### Trailer policy
Trailers are optional:
- if a trailer is available, show it
- if a trailer is not available, do not exclude the result

## 6. Product Modes

### A. Discover something to watch
User provides what they want by text or voice, answers a few clarifying questions, and gets 3 to 5 recommendations.

### B. Remember a title
User describes what they remember, the system proposes candidates, and asks narrowing questions until the correct title is confirmed.

### C. Learn over time
The app improves based on:
- Trakt bootstrap import
- onboarding questions
- in-app feedback
- watch confirmations
- saved and disliked titles

## 7. UX and Screen Plan

### A. Choose User
This is always the landing screen.

#### Required UI
- user avatar tiles
- display names
- create user button
- subtle admin badge
- simple tap-to-enter

#### Behavior
- app always opens here
- once a user is selected, that session remains active until switched
- a `Switch User` action must be visible and easy to access from every screen

### B. Home
Simple action-first dashboard.

#### Primary actions
- Find a Movie
- Find a TV Show
- Find Something for Us
- Help Me Remember a Title
- Continue Previous Search
- Watchlist

#### Secondary UI
- text input field
- microphone button
- recent searches
- recently saved items

### C. Discover
Structured, but conversational.

#### Inputs
- text entry
- voice transcript
- quick option chips such as:
  - action
  - sci-fi
  - thriller
  - family-friendly
  - hidden gem
  - short runtime
  - highly rated

#### Behavior
- ask only the minimum useful clarifying questions
- aim for 1 to 3 follow-up questions before first results when possible

### D. Remember a Title
Focused mode for vague-memory title recall.

#### UI components
- open prompt area
- microphone input
- extracted clue summary
- candidate result cards
- narrowing question panel

### E. Result cards
Each result should show:
- poster
- title + year
- movie/show badge
- short summary
- quality indicators
- content rating if known
- local availability badge when relevant
- trailer button if available
- short explanation for why it matched
- thumbs up/down
- save/watch later action

### F. Profile
- onboarding status
- Trakt connection status
- genre likes/dislikes
- hidden gem openness
- content tolerance
- watch history summary
- saved items

### G. Admin
- source connection health
- metadata refresh tools
- Trakt re-sync
- Jellyfin re-sync
- user management
- app status

## 8. Recommendation Engine Design

### Pipeline

#### Step 1: intake
Input comes from:
- typed text
- voice transcript
- quick action preset

#### Step 2: structured interpretation
Extract:
- media type
- genre
- mood/tone
- release era
- runtime preference
- darkness/intensity tolerance
- quality preference
- hidden-gem openness
- solo vs shared session

#### Step 3: decide whether AI is needed
Use AI only when:
- text is ambiguous
- clues are fuzzy
- the request is nuanced
- the system needs a smart next question

Skip AI when:
- the request is already structured
- quick actions define intent clearly
- deterministic filters are enough

#### Step 4: candidate generation
Pull from:
- TMDB search/discover
- local Jellyfin availability matches
- Trakt-informed related candidates
- one hidden-gem branch

#### Step 5: hard filtering
Remove:
- wrong media type
- hard-excluded genres/themes
- already disliked items
- already watched items when excluded
- runtime misses
- content rating or tolerance misses

#### Step 6: weighted scoring
Use the agreed weighted model:
- user taste fit
- critic/audience quality composite
- session fit
- shared-user fit when applicable
- diversity/freshness
- local availability boost
- hidden-gem bonus

#### Step 7: result shaping
Return:
- 3 strongest matches
- 1 hidden gem
- 1 optional curveball

#### Step 8: feedback capture
After a user confirms interest:
- watching now
- later today
- already seen

Then request:
- thumbs up/down now
- or store a follow-up request

## 9. Title Recall Engine Design

### Goal
Identify a specific movie or TV show from incomplete memory.

### Flow

#### Intake
User describes remembered details.

#### Clue extraction
Parse for:
- movie or show
- era
- actors
- setting
- country
- plot details
- relationships
- tone
- memorable scenes
- animation vs live action

#### Candidate generation
Search:
- TMDB titles
- TMDB people
- Jellyfin library
- local metadata cache

#### Clarification selection
Ask the single highest-value narrowing question next, for example:
- Was it a movie or a series?
- Was it animated or live action?
- Roughly what decade?
- Do you remember any actor?
- Was it set mostly in a specific country?
- Was there a romance subplot?

#### Confirmation
Once confirmed:
- show full title details
- ask watched/already seen
- capture feedback or save action

## 10. AI Use Policy

### AI is allowed for
- interpreting free-text discovery requests
- extracting fuzzy title-recall clues
- generating the next clarifying question
- generating concise explanation text

### AI is not allowed for
- acting as the final recommendation engine by itself
- inventing ratings or metadata
- bypassing source-of-truth APIs
- deciding final ranking without the scoring system
- silently extending long-running searches

### Response time rules
- Normal target: 15 seconds
- Soft ceiling: 20 seconds
- One-time extension: 25 seconds max

If the extension is used:
- the UI must clearly indicate refinement is happening
- the extension should be rare
- if confidence is still weak, ask another question rather than stall longer

## 11. Data Model Plan

### Core tables

#### Users
- `users`
- `user_profiles`
- `user_avatars`

#### Preferences and feedback
- `user_preferences`
- `user_genre_preferences`
- `user_feedback`
- `user_watch_history`
- `user_watchlist`
- `pending_rating_requests`

#### Media
- `titles`
- `title_external_ids`
- `title_metadata`
- `title_people`
- `title_videos`
- `title_watch_providers`
- `title_local_availability`

#### Sessions
- `search_sessions`
- `conversation_turns`
- `recall_sessions`
- `voice_transcripts`
- `recommendation_results`

#### Integrations and operations
- `source_connections`
- `sync_jobs`
- `app_settings`
- `audit_logs`

### Schema rule
TMDB ID is the canonical title ID. Trakt IDs, IMDb IDs, Jellyfin item IDs, and local file references map into `title_external_ids`.

## 12. API Plan

### User/profile endpoints
- `GET /api/users`
- `POST /api/users`
- `PATCH /api/users/:id`
- `POST /api/users/:id/select`
- `GET /api/users/:id/profile`

### Recommendation endpoints
- `POST /api/discover/start`
- `POST /api/discover/respond`
- `GET /api/discover/:sessionId/results`
- `POST /api/discover/:sessionId/feedback`

### Title recall endpoints
- `POST /api/recall/start`
- `POST /api/recall/respond`
- `GET /api/recall/:sessionId/candidates`
- `POST /api/recall/:sessionId/confirm`

### Integration endpoints
- `POST /api/integrations/tmdb/test`
- `POST /api/integrations/trakt/connect`
- `POST /api/integrations/trakt/sync`
- `POST /api/integrations/jellyfin/test`
- `POST /api/integrations/jellyfin/sync`

### Voice endpoint
- `POST /api/voice/transcribe`

### Admin endpoints
- `GET /api/admin/status`
- `POST /api/admin/refresh-metadata`
- `GET /api/admin/sync-jobs`

## 13. PC Preparation Tasks

This section replaces the old NAS-hosting preparation steps.

### A. Operating system readiness
Complete these tasks on the Windows PC:
- fully update Windows
- confirm the PC name and local admin access
- confirm enough free disk space remains on the NVMe drive
- create a dedicated working folder for the project
- decide whether backups will also be copied to the NAS

### B. Install required software
Install:
- Docker Desktop for Windows
- Git
- Node.js LTS
- Python 3.12+
- VS Code or preferred IDE
- a terminal you are comfortable using
- optional: Postman or Insomnia for API testing

### C. Enable WSL2
Enable WSL2 and configure Docker Desktop to use the WSL2-based engine.

### D. Configure Docker Desktop
Complete these checks:
- Docker Desktop starts successfully
- WSL2 backend is enabled
- Linux containers mode is active
- Docker Compose works from terminal
- choose a reasonable Docker data location if you do not want default storage on `C:`
- confirm Docker survives reboot and starts cleanly

### E. Project directory structure
Create a structure like:

```text
media-discovery-app/
  frontend/
  backend/
  infra/
    docker/
    env/
  docs/
  scripts/
  backups/
  logs/
```

### F. Networking preparation
Complete these network tasks:
- assign or reserve a stable LAN IP for the Windows PC
- confirm the Windows firewall allows the app ports you choose
- test that another device on the LAN can reach a simple local web server on the PC
- record the NAS IP and Jellyfin URL
- assign or reserve a stable LAN IP for the NAS too

### G. NAS-side preparation
Complete these NAS tasks:
- confirm Jellyfin is running and reachable from the Windows PC
- confirm any required API key or service credentials
- confirm any required NAS shares are reachable if direct file access will be used
- optionally create a NAS folder for app backup copies

### H. Secret and credential preparation
Prepare:
- TMDB API key
- Trakt client credentials
- Jellyfin base URL and API key
- AI provider API key
- STT provider API key
- Postgres password
- app secret key

Store them in `.env` files, never in source code.

### I. Development sanity checks
Before writing app code, verify:
- Docker Desktop works
- `docker compose` works
- Node runs
- Python runs
- Git is configured
- the PC can reach Jellyfin
- another LAN device can reach a test web service on the PC

## 14. Phased Task Layout

### Phase 0: host and development environment setup
#### Tasks
- complete all PC preparation tasks
- define repo structure
- decide monorepo or two-repo layout
- scaffold React + Tailwind frontend
- scaffold FastAPI backend
- stand up Postgres locally
- define `.env` strategy
- define Docker Compose baseline
- document coding standards
- define logging and error handling patterns
- confirm backend connectivity to Jellyfin on NAS
- confirm frontend/backend availability from another LAN device

#### Deliverables
- running frontend shell
- running backend shell
- running database
- containerized local dev environment
- confirmed LAN connectivity
- confirmed NAS connectivity

#### QA checks
- app boots cleanly
- frontend can call backend health endpoint
- DB migrations run successfully
- environment variables load correctly
- Docker containers restart cleanly
- backend can reach Jellyfin on the NAS
- app is reachable from phone/tablet on the LAN

### Phase 1: core data and integrations
#### Tasks
- create initial schema
- implement TMDB connector
- implement title search
- implement title details endpoint
- implement Jellyfin connector
- ingest local availability
- implement Trakt connection and bootstrap import

#### Deliverables
- titles stored locally
- external IDs mapped
- Trakt history imported per user
- Jellyfin availability flags working

#### QA checks
- one title resolves consistently across TMDB, Trakt, and Jellyfin
- missing trailer does not exclude a title
- sync jobs are idempotent
- failed external calls are logged and retried sensibly

### Phase 2: users and onboarding
#### Tasks
- build Choose User screen
- create user flow
- avatar support
- admin flag handling
- onboarding questions
- store initial preferences

#### Deliverables
- profile picker working
- new users created in-app
- preferences persisted

#### QA checks
- switching users changes recommendation context correctly
- one user’s likes/dislikes do not leak into another’s
- admin-only controls are hidden from non-admins

### Phase 3: discover flow
#### Tasks
- build discover UI
- create structured query model
- implement deterministic filters
- implement scoring engine
- build clarifying-question logic
- add hidden gem shaping
- add explanation text

#### Deliverables
- end-to-end recommendation flow
- 3 to 5 results returned reliably

#### QA checks
- same input produces stable results absent new data
- hidden gem result appears only when confidence supports it
- results always satisfy hard filters
- soft ceiling and extension behavior works correctly

### Phase 4: title recall flow
#### Tasks
- build recall UI
- implement clue extraction
- build candidate generation
- implement question refinement loop
- add confirmation flow

#### Deliverables
- recall mode identifies titles from fuzzy memory

#### QA checks
- known test cases return expected candidates
- narrowing questions reduce ambiguity
- confirmation logs feedback correctly

### Phase 5: voice input
#### Tasks
- add mic UI
- add browser audio capture
- integrate STT API
- show transcript review/edit
- send transcript into discover/recall flows

#### Deliverables
- voice input works for both primary modes

#### QA checks
- transcript can be edited before submission
- failed transcription degrades gracefully to text entry
- mobile browser microphone flow works on the devices used most

### Phase 6: feedback loop and reminders
#### Tasks
- implement watched now/later/already seen prompt
- capture thumbs up/down
- create pending rating request logic
- surface reminders in-app
- optionally add browser notification groundwork later

#### Deliverables
- feedback loop improves user profile quality

#### QA checks
- pending reminders appear for the correct user only
- duplicate reminders are not created
- feedback influences future ranking

### Phase 7: admin and hardening
#### Tasks
- build admin dashboard
- add source health checks
- add re-sync controls
- define backup/export strategy
- add audit and debug tooling
- final mobile polish
- optionally configure NAS backup target

#### Deliverables
- operationally maintainable v1

#### QA checks
- admin actions are logged
- failed syncs are visible
- system recovers from bad external responses
- backup and restore tested

## 15. QA Plan

### Functional QA
Verify:
- user creation
- user switching
- discover flow
- title recall flow
- voice input
- Trakt import
- Jellyfin sync
- admin actions
- feedback loop

### Data QA
Verify:
- TMDB IDs remain canonical
- external ID mapping is correct
- local availability flags are accurate
- duplicate title records do not proliferate
- watched status remains user-specific

### UX QA
Verify:
- app is easy on mobile
- switch user is visible everywhere
- clarifying questions are short and useful
- result cards are readable on phone screens
- loading states are understandable

### Performance QA
Verify:
- normal requests stay under 15 seconds
- soft ceiling under 20 seconds is respected
- extension logic never exceeds 25 seconds
- expensive AI calls are avoided for simple queries
- metadata sync jobs do not degrade UI responsiveness significantly

### Failure-mode QA
Verify:
- TMDB unavailable
- Trakt unavailable
- Jellyfin unavailable
- AI provider timeout
- STT failure
- database restart
- container restart
- PC reboot
- NAS reboot or temporary unavailability

The app should fail gracefully and explain what happened.

## 16. Deployment and Home-Network Implementation Guide

### A. Local development before stable deployment
Develop locally on the Windows PC first.
Do not treat deployment as a separate late-stage activity.
Your dev environment and your primary runtime environment should stay aligned.

### B. Core runtime model
Run these on the Windows PC:
- frontend container
- backend container
- postgres container

Optional later:
- worker container
- reverse proxy
- redis only if background workflow complexity justifies it

### C. Networking model
The app is LAN-only for v1.

Suggested port pattern:
- frontend: `3000`
- backend: `8000`
- postgres: internal only

Requirements:
- other household devices must be able to reach the frontend via the PC’s LAN IP
- backend must be able to reach Jellyfin on the NAS
- the Windows firewall must permit the selected app ports

### D. Persistent storage strategy
Persist outside containers:
- Postgres data
- backend logs
- metadata cache
- backups

Optional:
- copy backup archives to NAS on a schedule

### E. Deployment steps
1. Finish PC preparation tasks.
2. Create project directory structure.
3. Create `.env` files for local and deployment use.
4. Build frontend and backend images.
5. Create Docker Compose config for the stack.
6. Start the stack locally on the PC.
7. Verify frontend access on the PC.
8. Verify frontend access from another LAN device.
9. Verify backend health endpoint.
10. Create admin profile.
11. Connect TMDB, Trakt, and Jellyfin.
12. Run the first metadata sync.
13. Test discover flow.
14. Test title recall flow.
15. Test user switching.
16. Confirm backups are being written where expected.

### F. Post-deployment operational tasks
- schedule DB backups
- schedule metadata refreshes
- schedule Trakt syncs
- monitor Docker container health
- monitor PC RAM, CPU, and disk usage
- occasionally prune old images/containers
- optionally mirror backup files to the NAS

### G. Resource caution
The Windows PC has plenty of room for this stack.
Do not let that tempt you into overbuilding v1.
Avoid adding:
- local heavy LLM hosting
- vector DBs
- unnecessary queue infrastructure
- bloated observability stacks
- extra services that do not materially improve the product

## 17. Guardrails to Avoid Typical Vibecoder Mistakes

- Do not let AI choose final results directly
- Do not skip canonical ID mapping
- Do not merge household taste into one user model
- Do not overbuild voice before core search works
- Do not rely on trailers being present
- Do not design the UI as a generic chatbot
- Do not start with remote access
- Do not ship without debug logs explaining why recommendations were scored as they were
- Do not let stronger hardware justify unnecessary complexity in v1

## 18. Immediate Next Steps

1. Complete PC preparation and tooling setup.
2. Create the repo structure and choose frontend/backend layout.
3. Scaffold React + Tailwind frontend.
4. Scaffold FastAPI backend.
5. Stand up Postgres with Docker Desktop.
6. Define initial schema and migrations.
7. Implement TMDB connector and title model first.
8. Add Choose User flow and admin flag.
9. Add Discover flow with deterministic filters before any AI.
10. Add AI-assisted interpretation only after deterministic logic is proven.
11. Add Trakt and Jellyfin sync.
12. Add Recall mode.
13. Add voice input.
14. Run the full QA checklist.
15. Configure LAN access from household devices.
16. Establish backup flow, optionally including NAS backup copies.
