# Acadex — Deployment (Milestone 13)

This documents how to deploy Acadex on affordable/free infrastructure. It's
written as a concrete runbook, not a general survey — pick either path and
follow it end to end. No live environment was provisioned as part of this
milestone (that requires real cloud accounts/credentials this repo doesn't
have); what's here is what a deploy actually requires, verified against the
Dockerfiles and environment variables the app already uses.

## Recommended: Railway (or Render) + Vercel

A modest three-service split that fits comfortably in each provider's free/
starter tier for early traffic:

- **PostgreSQL** — Railway/Render managed Postgres.
- **Backend (FastAPI)** — deployed from `backend/Dockerfile`.
- **Frontend (Next.js)** — Vercel (zero-config for Next.js) or the same
  provider as the backend using `frontend/Dockerfile`.

### 1. Database

Provision a Postgres instance. Note the connection string — it becomes
`DATABASE_URL` (Railway/Render both give you one in
`postgresql://user:pass@host:port/db` form; SQLAlchemy needs the
`+psycopg2` driver marker, so use
`postgresql+psycopg2://user:pass@host:port/db`).

### 2. Backend

Deploy `backend/` as a Docker service (the existing `backend/Dockerfile`
needs no changes). Set these environment variables:

| Variable | Production value |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | the Postgres connection string above |
| `SECRET_KEY` | a fresh random value — generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`. The app refuses to start in production with the placeholder default (see `docs/SECURITY.md`). |
| `CORS_ORIGINS` | your deployed frontend origin, e.g. `https://acadex.vercel.app` |
| `PUBLIC_BASE_URL` | this backend service's own public URL, e.g. `https://acadex-api.up.railway.app` — used to build absolute upload URLs |
| `STORAGE_BACKEND` | `local` works for a first deploy but **does not persist across redeploys/restarts on most PaaS platforms** (ephemeral filesystem) and won't scale past one instance. Move to an S3-compatible bucket (Cloudflare R2, Backblaze B2, AWS S3) before real users start uploading question photos — implement `S3StorageBackend` in `app/storage/base.py` (the interface is already there; only that one class is unimplemented) and set `STORAGE_S3_*`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | defaults are reasonable; adjust if desired |

Run once after each deploy (migrations, not auto-applied on boot by design —
a failed migration should stop a deploy, not run silently):

```bash
alembic upgrade head
python -m scripts.create_admin you@example.com "a-strong-password" "Your Name"
```

Health check endpoint for the platform's health-check config: `GET /api/v1/health`.

### 3. Frontend

Deploy `frontend/` to Vercel (or as a Docker service using
`frontend/Dockerfile`). Set:

| Variable | Production value |
|---|---|
| `NEXT_PUBLIC_API_URL` | the backend's public URL + `/api/v1`, e.g. `https://acadex-api.up.railway.app/api/v1` |

Vercel builds with `npm run build` / serves with `next start` automatically;
no other config needed for this repo (App Router, no custom server).

### 4. Post-deploy checklist

- [ ] `GET /api/v1/health` returns `{"status": "ok"}`.
- [ ] Frontend loads and can register/log in against the deployed backend
      (checks `CORS_ORIGINS` and `NEXT_PUBLIC_API_URL` are correctly paired).
- [ ] `python -m scripts.seed_content` if you want sample content live, or
      start authoring real content via the teacher/admin dashboards instead.
- [ ] Uploaded question-thread images actually load (checks
      `PUBLIC_BASE_URL`/storage backend).
- [ ] `SECRET_KEY` is not the placeholder (the app already enforces this at
      startup — this is just a reminder the check exists).

## Local "deployment" (docker-compose)

For staging-like local runs, `docker-compose.yml` at the repo root already
runs Postgres + backend + frontend together:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

This is what CI or a self-hosted box would run too, with the same env vars
swapped for real production values per the table above.

## What's deliberately not done here

- **CI/CD pipeline** — not set up. `docker compose build` and `pytest tests/`
  (see `docs/SECURITY.md`) are the checks a pipeline should run before
  deploy; wiring them into GitHub Actions or similar is straightforward but
  out of scope until there's a hosting target to deploy to.
- **CDN / image optimization / autoscaling** — not needed at MVP traffic
  levels; revisit under `docs/DATABASE_SCHEMA.md`'s scalability notes once
  there's real usage data.
- **S3-compatible storage** — interface is ready (`app/storage/base.py`),
  implementation isn't, since it needs a real bucket/credentials to build
  and test against.
