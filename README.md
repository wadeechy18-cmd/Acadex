# Acadex

A free education platform for GCSE, International A-Level, and first-year
university Computer Science students — video lessons, notes, practice questions,
quizzes, past papers, and a student-teacher discussion community, built on an
architecture that supports future paid content, live classes, and AI tutoring
without a rewrite.

See `docs/ARCHITECTURE.md`, `docs/DATABASE_SCHEMA.md`, and `docs/MILESTONES.md`
for the full design.

## Stack

- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL

## Getting started (local development)

### Option A — Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

- Backend API: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:3000

### Option B — run services directly

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then point DATABASE_URL at your local Postgres
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Project layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations
frontend/   Next.js app
docs/       Architecture, database schema, milestone plan
```

## Status

Milestone 1 (project architecture) is complete. Authentication (Milestone 2) is
next — see `docs/MILESTONES.md`.
