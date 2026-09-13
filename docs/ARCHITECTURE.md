# Acadex Architecture

Acadex is a three-portal SaaS for schools and teachers: **School** (management,
timetabling, absence/cover automation), **Teacher** (AI-assisted lesson
planning), and **Student** (not yet built — shows "Coming Soon"). This
document describes the system as it stands after the ground-up rebuild
(replacing an earlier, unrelated student-learning platform).

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| AI | Anthropic, via a provider abstraction (`app/ai/provider.py`) — swappable, and the app runs without a key configured (AI endpoints return 503 rather than the app failing to start) |
| Deterministic scheduling | Google OR-Tools CP-SAT (`app/planning/substitution_optimizer.py`) — **never AI** |
| Testing | pytest (backend); `tsc --noEmit` + `next build` + live Playwright checks (frontend) |

## Multi-tenancy

A **School** is a real, isolated tenant — never a teacher's personal account
standing in for one. `SchoolMembership` is a join table between `User` and
`School` carrying its own role (`ADMIN` / `TEACHER`), distinct from
`User.role` (`SCHOOL_ADMIN` / `TEACHER` / `STUDENT`, the account type decided
at registration). A school admin is a structurally different account from a
teacher from the moment of registration — not a teacher record with a flag.

Every school-scoped table carries a `school_id` (or reaches one through a
parent row) and every school-scoped service function funnels through
`app.services.school_service.assert_school_member(db, actor, school_id,
min_role=...)` before touching any row — this codebase's single choke point
for tenant isolation, since it doesn't use Postgres row-level security. See
`docs/ARCHITECTURE.md`'s own test suite (`backend/tests/test_*.py`) for the
isolation tests proving one school can never see another's data.

A teacher belongs to at most one school today. `Class` and `Resource` are
teacher-owned (no `school_id` column) rather than school-owned — a school
admin can still browse a teacher's classes/lesson plans read-only via a join
through `SchoolMembership` where needed (e.g. `GET /schools/{id}/classes`,
`GET /schools/{id}/lesson-plans`), without those rows belonging to the school
outright.

## Database (selected entities, grouped by domain)

- **Identity**: `User`, `TeacherProfile`, `SchoolAdminProfile`, `School`,
  `SchoolMembership`.
- **Curriculum**: `Curriculum` → `KeyStage` → `YearGroup` → `Subject` →
  `ProgrammeOfStudy` → `CurriculumTopic` → `Objective`. Only England / the
  English National Curriculum is seeded today (`scripts/seed_curriculum.py`,
  ETL'd from bundled weekly-lesson JSON), but the shape supports adding a
  second country/curriculum without a schema change.
- **Resources**: `Resource` (PDF/DOCX/PPTX/image/text, extract→clean→chunk
  pipeline in `app/planning/text_extraction.py`; images are stored but not
  text-extracted yet).
- **Lesson planning**: `LessonPlan`, `LessonPlanVersion` (append-only —
  "current" is always the highest `version_number`, never a separate
  pointer column), `LessonPlanVersionResource`.
- **Classes & tasks**: `Class`, `Task`.
- **Timetable**: `AcademicYear`, `Room`, `TimeSlot` (day-specific, e.g.
  "Monday Period 1"), `Timetable`, `TimetableEntry`,
  `TeacherSubjectQualification`, `TeacherAvailability`.
- **Absence & cover**: `TeacherAbsence`, `AffectedLesson`, `SubstitutionPlan`,
  `SubstitutionAssignment`, `TimetableException` (a dated override of one
  `TimetableEntry` — the normal timetable is never modified), `Notification`.
- **Audit**: `AuditLog` — one row per school-admin mutation.

All tables use UUID primary keys and `created_at`/`updated_at` timestamps
(`app/db/base.py`'s `UUIDPKMixin`/`TimestampMixin`).

## The AI Lesson Plan Builder

A teacher fills in subject / year group / topic (from the curriculum browse
API, or free text) / duration / ability level / objectives / instructions /
resources to draw on. `app/services/lesson_plan_service.py` builds a prompt
(`app/planning/lesson_generation.py`) including curriculum objectives and
resource excerpts, calls the `AIProvider` for one structured-JSON response
(a 19-section `LessonPlanContent` schema — never one text blob), then:

1. **Normalizes the timeline** (`app/planning/timeline.py`) against the
   requested duration — the model is asked to produce a timeline spanning
   the full lesson, but this is verified and repaired deterministically
   rather than trusted at face value.
2. **Runs the safeguarding check** (`app/planning/safeguarding.py`) — a
   narrow, keyword-based flag for human review. It never blocks or edits
   content and never claims to guarantee legal or policy compliance; it's a
   software safeguard, not a substitute for school policy or professional
   judgement.
3. Persists a new `LessonPlanVersion`.

Editing supports save-in-place (current version only), save-as-new-version,
restoring an old version (copies its content into a new version — history is
never overwritten), duplicating a whole plan, and regenerating a single
section (via a one-field Pydantic schema built on the fly with
`pydantic.create_model`, so a regeneration call can never touch any other
section). Export to PDF/DOCX (`app/export/`) and print are built against the
same structured content.

## Timetable & absence/cover automation

The timetable is a grid of `TimetableEntry` rows (teacher × subject × class ×
room, per `TimeSlot`) built by a school admin, with hard conflict checks in
`app/services/timetable_service.py` (never double-book a teacher, class, or
room in the same slot — enforced as an application-level check with a clear
409, not a DB constraint, since class/room are optional).

Reporting a `TeacherAbsence` deterministically computes every affected
`TimetableEntry` for that date (`app/services/absence_service.py`) — no AI —
by mapping the date to a weekday and matching entries against any timetable
whose academic year covers that date.

**Substitution is the core workflow connecting the two product halves.**
`app/planning/substitution_optimizer.py` is a pure module (no DB, no HTTP)
wrapping Google OR-Tools CP-SAT:

- **Hard constraints are structural**, not scored: a lesson gets at most one
  candidate; a candidate covering one lesson at a time slot can't also cover
  a different lesson at that same slot in the batch. Callers
  (`substitution_service`) pre-filter each lesson's candidate list to
  exclude the absent teacher, anyone unavailable at that slot, and anyone
  with a genuine timetable conflict there — those never appear as
  candidates at all.
- **Soft constraints** (qualified subject, workload balance, avoiding
  repeat cover) are scored, but the objective weights *filling a lesson*
  far above any quality difference — the solver maximises coverage first.
- **A lesson with no valid candidate is left unfilled**, with a stored
  reason. Acadex never invents an assignment to fill the gap.

An admin reviews the proposed `SubstitutionPlan`, can manually reassign or
unassign any row, then **approves** or **rejects** it. Approval creates a
`TimetableException` per lesson (the normal timetable is untouched) and a
`Notification` for each substitute. A substitute's Cover view
(`/teacher/cover`, `GET /timetable-exceptions/mine`) surfaces the absent
teacher's most recently updated lesson plan for that subject/class as a
best-effort match — there is no formal link from a timetable slot to a
lesson plan yet, so this is a heuristic, and the UI says so.

## Security

- JWT access/refresh tokens (`app/core/security.py`), password reset tokens
  fingerprinted against the current password hash so a token issued before
  a password change is automatically invalidated.
- Rate limiting on auth endpoints (slowapi).
- File uploads validated by content type and size (`app/storage/base.py`);
  uploaded files are served only through authenticated, ownership-checked
  routes (`GET /resources/{id}/file`) — never a public static mount.
- RBAC via `app/api/deps.py` (`require_teacher`, `require_school_admin`) and
  the tenant-isolation choke point described above.
- `AuditLog` records school-admin mutations (membership changes, task and
  timetable-entry CRUD, absence reporting, substitution plan
  approval/rejection/reassignment) — readable at
  `GET /schools/{id}/audit-log`, admin-only, never editable through the API.

## Known simplifications / follow-up work

- `Term` (from the brief's `AcademicYear`/`Term` pair) isn't modelled
  separately — `Timetable` scopes directly to `AcademicYear`.
- Resource text extraction doesn't cover images yet (stored and
  downloadable, not OCR'd).
- A handful of sidebar links (`/teacher/calendar`, `/teacher/settings`,
  `/school/subjects`) remain unbuilt placeholders from early increments;
  they were not part of any approved increment's scope.
- The substitute's "Cover Lesson" lesson-plan match is a best-effort
  heuristic (same owner, subject, and class), not a formal schedule link.
- Student accounts, an AI tutor, adaptive learning, a marketplace, live
  classes, payments, and a past-paper system are explicitly out of scope
  for this phase.

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
python -m scripts.seed_curriculum   # England / English National Curriculum browse data
python -m scripts.seed_dev_data     # optional: a demo school/admin/teachers/timetable/task
uvicorn app.main:app --reload
pytest

# Frontend
cd frontend
npm install
npm run dev
npx tsc --noEmit && npm run build
```
