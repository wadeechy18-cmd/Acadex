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

A teacher either fills in the detailed form (subject / year group / topic /
duration / ability level / objectives / instructions / resources to draw
on), or types one sentence into the **quick-generate** box (e.g. "Make me a
lesson plan for tomorrow on separating mixtures"). Both paths converge on
`app/services/lesson_plan_service._generate_full_lesson`.

**Quick-generate** (`POST /lesson-plans/quick-generate`,
`quick_generate_from_text`) is resource-first and AI-minimal by design:

1. One small AI call (`INTENT_SYSTEM_PROMPT`) extracts structured intent
   (`app.schemas.quick_lesson.QuickLessonIntent`: subject/year-group
   wording, topic, a raw date phrase, duration, ability level) from the
   teacher's sentence — it never generates lesson content itself.
2. Everything after that is deterministic Python, never AI:
   `app/planning/date_resolution.py` resolves "tomorrow" / a weekday name /
   an ISO date against today's real date; `app/planning/entity_matching.py`
   matches the extracted wording against the teacher's real
   Subject/YearGroup/CurriculumTopic rows (falling back to the subject/year
   group of the teacher's most recently created plan when unspecified, and
   a 422 — never a guess — when neither can be resolved);
   `app/planning/resource_matching.py` then searches the teacher's own
   resource library (tag match on `Resource.subject_id`/`year_group_id`
   plus a keyword-overlap fallback for untagged files) and returns only the
   handful of relevant resources — the full library is never sent to the
   model.

**Generation** (shared by both entry points) builds a prompt
(`app/planning/lesson_generation.py`) from curriculum objectives and the
matched resource excerpts, calls the `AIProvider` for one structured-JSON
lesson (a 19-section `LessonPlanContent` schema — never one text blob),
then makes two further small, single-purpose calls for a **worksheet**
(`WorksheetContent`: recall/understanding/application/challenge questions)
and **homework** (`HomeworkContent`: instructions, tasks, estimated
minutes) — generated automatically with every lesson, never a separate
ask. After generation:

1. **Normalizes the timeline** (`app/planning/timeline.py`) against the
   requested duration — the model is asked to produce a timeline spanning
   the full lesson, but this is verified and repaired deterministically
   rather than trusted at face value.
2. **Runs the safeguarding check** (`app/planning/safeguarding.py`) over
   the lesson, worksheet and homework text together — a keyword-based flag
   (self-harm, weapons, sexual content, extremism, substance misuse, unsafe
   practical activities/equipment, activities needing a risk assessment or
   school permission, online safety/personal information risk, one-to-one
   or physical contact risk, bullying, and discriminatory content) for
   human review. It never blocks or edits content and never claims to
   guarantee legal or policy compliance; it's a software safeguard, not a
   substitute for school policy or professional judgement.
3. Persists a new `LessonPlanVersion` (content, worksheet, homework
   together).

Editing supports save-in-place (current version only, including edits to
the worksheet/homework), save-as-new-version, restoring an old version
(copies its content into a new version — history is never overwritten),
duplicating a whole plan, and regenerating a single lesson section, the
whole worksheet, or the whole homework independently (each via a
single-purpose schema, so a regeneration call can never touch anything
else). Export to PDF/DOCX (`app/export/`) and print are built against the
same structured content, for the lesson, worksheet and homework
independently.

**Bangla translation**: a teacher can request a বাংলা translation of any
version (`POST .../translate`, `app/planning/translation.py`) — one AI
call producing the same structured shape in Bangla (preserving formulas,
units, numbers and curriculum codes untouched, and giving technical terms
as "বাংলা (English)"), cached on the version (`translation_bn`) so
switching the language toggle back and forth never re-triggers an AI call.
The English original is never mutated.

**Curriculum library** (`/teacher/lesson-plans/library`, `scripts/seed_lesson_plan_library.py`):
every EYFS/KS1 weekly lesson bundled in `app/curriculum_packs/` is mapped
once into a real, ready-made `LessonPlan` — no AI call — owned by a single
dedicated, `is_active=False` account (`LIBRARY_OWNER_EMAIL`) that can never
log in and exists purely to hold shared content. Any teacher can browse and
filter these; "using" one calls the existing `duplicate_plan` service
function to copy it into that teacher's own plans, fully editable from
there — the shared original is never modified in place.

## Timetable & absence/cover automation

The timetable is a grid of `TimetableEntry` rows (teacher × subject × class ×
room, per `TimeSlot`), buildable by hand or **auto-generated**: an admin adds
`ClassSubjectRequirement` rows (a class needs N periods/week of a subject),
then `POST .../generate` hands them, the school's `TeacherSubjectQualification`
and `TeacherAvailability` rows, and the timetable's `TimeSlot`s to
`app/planning/timetable_generation.py` — another pure CP-SAT module (never
AI, same as substitution below). It maximises total periods scheduled subject
to hard constraints (never double-book a class/teacher in a slot; at most one
period of the same requirement per day, so a subject spreads across the week
rather than clustering); a requirement that can't be fully met is reported as
a shortfall (requested vs. scheduled), never silently dropped or faked. Room
assignment is a simple first-fit greedy pass afterward, deliberately outside
the CP-SAT model (see that module's docstring) — a lesson with no room free
is still scheduled, just without one. Generating replaces every entry on that
timetable. Manual entry CRUD (with the same conflict checks, enforced at the
application level with a clear 409, not a DB constraint, since class/room
are optional) still works for hand-adjusting afterward.

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
- The `/teacher/calendar` and `/teacher/settings` sidebar links from early
  increments, and the school-side `/school/subjects`/`/school/resources`
  links, were never built and have been removed rather than left as dead
  links; they were not part of any approved increment's scope.
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
python -m scripts.seed_lesson_plan_library   # optional: ~1,800 ready-made EYFS/KS1 lesson plans
uvicorn app.main:app --reload
pytest

# Frontend
cd frontend
npm install
npm run dev
npx tsc --noEmit && npm run build
```
