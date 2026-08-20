# Acadex

A free education platform for GCSE, International A-Level, and first-year
university Computer Science students — video lessons, notes, practice questions,
quizzes, past papers, and a student-teacher discussion community, built on an
architecture that supports future paid content, live classes, and AI tutoring
without a rewrite.

See `docs/ARCHITECTURE.md`, `docs/DATABASE_SCHEMA.md`, `docs/MILESTONES.md`, and
`docs/SECURITY.md` for the full design.

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
python -m scripts.create_admin you@example.com "a-strong-password" "Your Name"
python -m scripts.seed_content   # optional: sample subjects/courses/questions
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Testing

```bash
createdb acadex_test   # once, alongside your regular acadex database
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

See `docs/SECURITY.md` for what the suite covers and what was reviewed by hand.

## Project layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, pytest suite
frontend/   Next.js app
docs/       Architecture, database schema, milestone plan, security review
```

## Status

All 13 milestones are complete: architecture, authentication, the full
learning hierarchy (levels → exam boards → subjects → courses → chapters →
topics → lessons), student dashboard/enrollment/progress/bookmarks, video +
notes, practice questions + quizzes, ask-a-question + discussions, teacher
and admin dashboards, past papers, search + notifications, an automated test
+ security review pass, and a deployment runbook (`docs/DEPLOYMENT.md`). See
`docs/MILESTONES.md` for details and the future live-classes/payments/
AI-tutor features the schema is already ready for.
