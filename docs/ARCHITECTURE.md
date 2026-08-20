# Acadex — Architecture

## Overview

Acadex is a modular monolith split into two deployable units that communicate over a
versioned JSON REST API:

- **backend/** — FastAPI + SQLAlchemy + PostgreSQL. Owns all business logic, auth,
  and data. Organized in layers so features can be added without touching unrelated
  code:
  - `app/models` — SQLAlchemy ORM models (the schema of record).
  - `app/schemas` — Pydantic request/response contracts (never expose ORM models
    directly).
  - `app/api/v1/endpoints` — thin HTTP route handlers, one router per resource area.
  - `app/services` — business logic used by endpoints (and later by background
    jobs / AI features) so logic isn't duplicated across routes.
  - `app/storage` — abstraction over file storage (local disk in dev, S3-compatible
    object storage in production) so upload code never talks to a provider SDK
    directly.
  - `app/db` — engine/session management.
  - `app/core` — settings, security primitives (hashing, JWT), shared config.
  - `alembic/` — versioned schema migrations. The schema is never hand-edited in
    production; every change is a migration.

- **frontend/** — Next.js (App Router) + TypeScript + Tailwind CSS. Talks to the
  backend only through `src/lib/api-client.ts`, never with hard-coded URLs scattered
  through components. Route groups mirror the learning hierarchy
  (level → exam board → subject → course → chapter → topic → lesson).

## Why this split

- **No rewrite for future features.** Payments, live classes, and AI tutoring are
  modeled in the schema now (see `docs/DATABASE_SCHEMA.md`) but not wired into any
  user-facing flow. Turning them on later is additive: new endpoints/services/UI,
  not a redesign.
- **Entitlements, not hard-coded "free".** Access to a resource is decided by an
  `Entitlement` check, which currently always resolves to "allowed" for MVP content.
  This means introducing paid content later doesn't require touching every place
  that currently assumes free access.
- **Storage abstraction.** Videos, images and documents are referenced by metadata
  rows (`Video`, `QuestionImage`, `PastPaperResource`) pointing at a storage key, not
  by hard-coded URLs in the frontend. Swapping local disk for S3/Cloudflare
  R2/Mux later touches one module (`app/storage`).
- **Role-based access control.** A single `User` table with a `role` enum
  (`student` / `teacher` / `admin`) plus per-role profile tables keeps auth simple
  now while still letting each role carry role-specific fields.

## Request flow

```
Browser (Next.js) --HTTPS/JSON--> FastAPI router --> service layer --> SQLAlchemy --> PostgreSQL
                                                   \-> storage abstraction --> object storage
```

## Environments

- **Local development:** `docker-compose.yml` runs Postgres, the FastAPI dev server
  (reload on), and the Next.js dev server together.
- **Configuration:** all secrets/URLs come from environment variables
  (`backend/.env`, `frontend/.env`), never committed. `.env.example` documents every
  variable.

## Non-goals for the MVP

Payments, live classes, and AI tutoring are schema-ready but intentionally not
exposed through any API route or UI in Milestone 1. See `docs/MILESTONES.md`.
