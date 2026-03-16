# What2Watch — Production Deployment Plan

## Current State

- **Deployment**: Docker Compose on a local Windows PC (LAN-only)
- **Auth**: None — client-side user selection, backend trusts `user_id` param
- **CORS**: `["*"]` (allow all origins)
- **Admin routes**: No access control
- **Secret key**: Hardcoded default `"change-me-in-production"`
- **Containers**: Running in dev mode (`--reload`, `npm run dev`)
- **Database**: PostgreSQL 16 with default credentials
- **HTTPS**: Optional (cert files), not enforced
- **Max users**: 5 (hardcoded limit)

---

## Phase 1: Security Hardening (Must-Do Before Public Access)

### 1.1 Authentication System
**Blocker: The app has zero authentication.**

Every API call trusts the client-supplied `user_id`. Any user can impersonate any other user, access admin endpoints, or delete watchlist items.

**Recommended approach (cost-effective):**
- Add **email + password auth** using FastAPI + python-jose (JWT)
- Store hashed passwords (bcrypt via passlib)
- Issue short-lived access tokens (15min) + refresh tokens (7d)
- Add `get_current_user` dependency to all routes
- Protect admin routes with `is_admin` check middleware
- Remove the 5-user limit or make it configurable

**Alternative (simpler but less flexible):**
- OAuth2 via a free provider (Google Sign-In, GitHub OAuth)
- Offloads password management entirely
- Still need JWT for session management

**Estimated effort**: 2-3 days

### 1.2 Secrets Management
- Generate a strong random `SECRET_KEY` (32+ bytes)
- Move all API keys to environment variables (already partially done)
- Never commit `.env` to git
- Rotate database credentials from defaults
- Use separate credentials per environment (dev/staging/prod)

### 1.3 CORS Lockdown
- Replace `["*"]` with the actual frontend domain
- Example: `CORS_ORIGINS=["https://what2watch.yourdomain.com"]`

### 1.4 Rate Limiting
- Add `slowapi` or similar to FastAPI
- Rate limit auth endpoints aggressively (5 attempts/min)
- Rate limit AI-powered endpoints (expensive — 10 req/min/user)
- Rate limit general API (100 req/min/user)

### 1.5 Input Validation
- Already using Pydantic schemas (good)
- Audit all endpoints for SQL injection (SQLAlchemy parameterizes, but verify raw queries)
- Sanitize user-generated text before passing to AI providers (prompt injection risk)

---

## Phase 2: Production Build Pipeline

### 2.1 Frontend
- Build static assets: `npm run build` (Vite outputs to `dist/`)
- Serve via Nginx or a CDN (not Vite dev server)
- Enable gzip/brotli compression
- Set cache headers for static assets (images, JS, CSS)
- **Current blocker**: Vite proxy handles `/api` routing — need Nginx or similar to reverse-proxy in production

### 2.2 Backend
- Remove `--reload` from uvicorn command
- Run with multiple workers: `uvicorn app.main:app --workers 4`
- Or use Gunicorn with uvicorn workers: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`
- Add structured logging (replace print statements)
- Add health check endpoint (`/health`)

### 2.3 Database
- Enable connection pooling (asyncpg pool or PgBouncer)
- Set up automated backups (pg_dump cron or managed DB snapshots)
- Run Alembic migrations as part of deploy pipeline

---

## Phase 3: Deployment Options (Cost Comparison)

### Option A: Single VPS (Most Cost-Effective) — Recommended to Start
**Monthly cost: $5-12/mo**

| Component | Service | Cost |
|-----------|---------|------|
| VPS | Hetzner CX22 (2 vCPU, 4GB RAM) | $4.50/mo |
| Domain | Namecheap/Cloudflare | $10/yr |
| SSL | Let's Encrypt (free) | $0 |
| DNS/CDN | Cloudflare Free | $0 |
| DB | PostgreSQL on same VPS | $0 |
| **Total** | | **~$5-6/mo** |

**Architecture:**
```
Cloudflare (DNS + CDN + SSL termination)
    ↓
Hetzner VPS ($4.50/mo)
├── Nginx (reverse proxy + static files)
├── Docker Compose
│   ├── backend (FastAPI + Gunicorn)
│   └── db (PostgreSQL 16)
└── Certbot (Let's Encrypt renewal)
```

**Pros**: Cheapest, simplest, full control
**Cons**: Single point of failure, manual scaling, you manage updates
**Capacity**: ~50-200 concurrent users comfortably

### Option B: Container Platform (Medium Scale)
**Monthly cost: $15-30/mo**

| Component | Service | Cost |
|-----------|---------|------|
| Containers | Railway / Render / Fly.io | $5-15/mo |
| Database | Managed PostgreSQL (Neon free tier or Supabase) | $0-10/mo |
| Frontend | Vercel / Cloudflare Pages (free) | $0 |
| Domain + SSL | Cloudflare | $0 |
| **Total** | | **~$15-25/mo** |

**Pros**: Auto-deploy from git, managed SSL, easy scaling, no server maintenance
**Cons**: More expensive, vendor lock-in, cold starts on free tiers
**Capacity**: ~200-1000 users

### Option C: Cloud Provider (Large Scale)
**Monthly cost: $30-100+/mo**

| Component | Service | Cost |
|-----------|---------|------|
| Compute | AWS ECS Fargate / GCP Cloud Run | $15-40/mo |
| Database | AWS RDS / GCP Cloud SQL | $15-30/mo |
| Frontend | S3 + CloudFront / GCS + CDN | $1-5/mo |
| Load balancer | ALB / Cloud LB | $15/mo |
| **Total** | | **~$50-90/mo** |

**Pros**: Auto-scaling, high availability, managed everything
**Cons**: Expensive, complex setup, overkill for early stage
**Capacity**: 1000+ users

---

## Phase 4: Cost Optimization for AI Calls

**This is the biggest variable cost.** Each discover/recall request calls an AI provider.

### Current AI costs per request (approximate):
| Provider | Model | Input/Output Cost | Est. per search |
|----------|-------|-------------------|-----------------|
| OpenAI | gpt-5.2 | Varies | ~$0.01-0.05 |
| Anthropic | claude-haiku-4-5 | $0.80/$4 per 1M tokens | ~$0.005-0.02 |
| Google | gemini-2.0-flash | Free tier available | ~$0.001-0.01 |

### Cost control strategies:
1. **Use the cheapest model that works** — Gemini Flash or Claude Haiku for most queries
2. **Cache AI responses** — Same query + same user prefs = cache hit (Redis or in-memory)
3. **Rate limit AI calls per user** — e.g., 20 searches/day free, then throttle
4. **Batch/debounce** — Don't call AI on every keystroke
5. **Set a monthly AI budget cap** — Track spend and disable when exceeded
6. **Pre-compute popular recommendations** — Cron job for trending content

### Projected AI costs at scale:
| Users | Searches/day | Monthly AI cost (Haiku) | Monthly AI cost (Gemini Flash) |
|-------|-------------|------------------------|-------------------------------|
| 50 | 100 | ~$30-60 | ~$3-10 |
| 500 | 1,000 | ~$300-600 | ~$30-100 |
| 5,000 | 10,000 | ~$3,000-6,000 | ~$300-1,000 |

**Recommendation**: Start with Gemini Flash or Claude Haiku + aggressive caching. At 50 users, AI is ~$3-30/mo. At 500+ users, caching becomes critical.

---

## Phase 5: Monitoring & Operations

### Essential (Day 1):
- **Uptime monitoring**: UptimeRobot (free for 50 monitors)
- **Error tracking**: Sentry (free tier: 5K events/mo)
- **Log aggregation**: Docker logs → file rotation (or Betterstack free tier)

### Nice to Have:
- **Metrics**: Prometheus + Grafana (self-hosted on same VPS)
- **AI cost dashboard**: Track spend per user/day
- **Database monitoring**: pg_stat_statements for slow queries

---

## Blockers & Risks

### Critical Blockers (Must Fix Before Launch)
| # | Blocker | Impact | Effort |
|---|---------|--------|--------|
| 1 | **No authentication** | Anyone can impersonate users, access admin | 2-3 days |
| 2 | **No HTTPS enforcement** | Credentials/tokens sent in plaintext | 1 hour (with Let's Encrypt) |
| 3 | **Default DB credentials** | Database compromise if port exposed | 30 min |
| 4 | **CORS allows all origins** | Cross-site request forgery | 10 min |
| 5 | **Admin routes unprotected** | Anyone can change AI settings, view all users | 1 day (after auth) |
| 6 | **Dev mode in production** | `--reload` watches files, performance hit | 30 min |
| 7 | **No production frontend build** | Vite dev server is not for production | 1 hour |

### High Risks
| # | Risk | Likelihood | Mitigation |
|---|------|-----------|------------|
| 1 | **AI cost blowout** | High if popular | Rate limits + budget caps + caching |
| 2 | **TMDB API rate limits** | Medium (40 req/10s) | Response caching, batch requests |
| 3 | **Single VPS failure** | Low-Medium | Automated backups, quick redeploy script |
| 4 | **API key leakage** | Low if managed | Never in git, rotate on suspicion |
| 5 | **Prompt injection via AI** | Medium | Sanitize user input, system prompt hardening |
| 6 | **Database growth** | Low (small data per user) | Monitor, archive old feedback |

### Medium Risks
| # | Risk | Notes |
|---|------|-------|
| 1 | TMDB ToS compliance | Verify usage at scale is allowed |
| 2 | AI provider ToS | Some prohibit caching responses |
| 3 | Content liability | Recommendations could surface inappropriate content |
| 4 | GDPR/privacy | If EU users: need data export/deletion, privacy policy |

---

## Recommended Deployment Roadmap

### Week 1: Security
- [ ] Implement JWT auth (email + password)
- [ ] Protect admin routes
- [ ] Lock down CORS
- [ ] Rotate all default credentials
- [ ] Add rate limiting

### Week 2: Production Build
- [ ] Create production Dockerfiles (multi-stage builds)
- [ ] Nginx config for reverse proxy + static files
- [ ] Production docker-compose (no dev modes)
- [ ] Alembic migration in deploy pipeline
- [ ] Health check endpoints

### Week 3: Deploy
- [ ] Provision VPS (Hetzner CX22)
- [ ] Domain + Cloudflare DNS
- [ ] Let's Encrypt SSL via Certbot
- [ ] Deploy with Docker Compose
- [ ] Automated backups (pg_dump to object storage)
- [ ] Uptime monitoring + Sentry

### Week 4: Cost Controls
- [ ] AI response caching (Redis or in-memory)
- [ ] Per-user rate limits on AI endpoints
- [ ] Monthly budget tracking dashboard
- [ ] Optimize AI prompts for fewer tokens

---

## Total Estimated Cost at Launch (50 users)

| Item | Monthly Cost |
|------|-------------|
| Hetzner VPS (CX22) | $4.50 |
| Domain | ~$1 (amortized) |
| Cloudflare DNS/CDN | $0 |
| SSL (Let's Encrypt) | $0 |
| AI (Gemini Flash + caching) | $3-10 |
| TMDB API | $0 (free) |
| Monitoring (free tiers) | $0 |
| **Total** | **~$8-16/mo** |

At 500 users with caching: **~$20-50/mo**
At 5,000 users: **~$100-300/mo** (upgrade VPS + AI costs dominate)
