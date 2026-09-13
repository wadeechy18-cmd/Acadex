# Acadex

An education SaaS platform with three entry paths — School, Teacher, and (coming soon)
Student. The first two real products are a **Teacher AI Lesson Plan Builder** aligned to the
English National Curriculum, and **School Management** covering teachers, classes, lesson
plan oversight, tasks, timetabling, and deterministic teacher-absence/cover automation.

## Stack

- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL
- **Scheduling:** Google OR-Tools (CP-SAT) — the timetable/substitution optimizer is
  deterministic constraint solving, never an LLM call

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

## Testing

```bash
createdb acadex_test   # once, alongside your regular acadex database
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Project layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, pytest suite
frontend/   Next.js app
```

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system design:
multi-tenancy, database schema, the AI Lesson Plan Builder, and the OR-Tools
timetable/absence/cover-substitution workflow.

## Status

The core rebuild is complete: identity & multi-tenancy, the England/English
National Curriculum hierarchy, teacher resources, the AI Lesson Plan Builder
(generation, versioning, section regeneration, export), classes/tasks/lesson
plan library search, the timetable grid with qualifications and
availability, absence detection, and the OR-Tools substitution optimizer
with admin approval. A handful of sidebar links remain unbuilt placeholders
(`/teacher/calendar`, `/teacher/settings`, `/school/subjects`) — see
`docs/ARCHITECTURE.md`'s "Known simplifications" section.
