# Acadex — Lesson Planner Architecture (Phase 0)

This document is the Phase 0 deliverable for extending Acadex from a student
learning platform into a Teacher + School lesson-planning platform, without
breaking the existing student product. It records what exists today, what's
being added, why, and the open decisions that need a call before Phase 1
starts. No lesson-planner code, migrations, or models exist yet — this is
architecture only.

## Status: all 10 phases complete

Phases 0–10 have all shipped (workspaces/classes, lesson plan CRUD, the
local no-AI planning engine, resource ingestion, optional AI enhancement,
worksheets/homework, the weekly planner, school admin, and PDF/DOCX
export). The sections below are the original Phase 0 design and are kept
as-written for context; where the shipped implementation deliberately
diverged, the reason is documented as a comment at the point of deviation
in code (e.g. `TeachingClass.subject_name`/`WeeklyPlan`'s per-organization
scoping) rather than edited back into this doc. Every deviation followed
the same rule this doc sets out: free text over a taxonomy-coupled FK
wherever EYFS/KS1/KS2 coverage would otherwise be impossible, and no
change shipped without tests plus a live check against a running backend
and frontend.

## 0. Correction to the brief's assumptions

The brief describes "existing Supabase/PostgreSQL setup" and "Supabase Row
Level Security". Acadex does not use Supabase anywhere — it's a plain
self-hosted PostgreSQL database via SQLAlchemy 2.0 + Alembic, with a fully
custom JWT auth system (`python-jose`, bcrypt, no sessions/cookies). There is
no Supabase Auth, Storage, or RLS to build on. Everywhere the brief says
"Supabase", read "PostgreSQL, accessed only through our own FastAPI layer".
Section 8 below addresses what "RLS where appropriate" means for a codebase
without Supabase.

## 1. Current state summary

- **Frontend**: Next.js 16 App Router, React 19, TypeScript, Tailwind. No
  state library beyond a single `AuthProvider` React context. No shared
  `<Navbar>` — each page builds its own header. No drag-and-drop, table,
  calendar, or rich-editor component exists yet.
- **Backend**: FastAPI, thin routers → service-layer functions → SQLAlchemy
  ORM (no raw SQL anywhere). Pydantic v2 schemas. One Alembic migration to
  date (`initial_schema`) — this feature is the first to add migrations
  incrementally.
- **Auth**: custom JWT, bearer-only. `get_current_user` / `require_roles(...)`
  dependencies. `User.role` is one flat, global enum: `student | teacher |
  admin`. Each role has exactly one profile row (`StudentProfile` /
  `TeacherProfile` / `AdminProfile`), 1:1 with `User`.
- **Existing "workspace-shaped" pattern**: `TeacherSubject` is a join table
  between `TeacherProfile` and `Subject` that scopes what a teacher may
  author; every mutating endpoint calls an `assert_can_manage_*` service
  function that checks this table. This is the direct ancestor of the new
  `organization_members` pattern below — same shape, wider scope.
- **Storage**: `StorageBackend` interface (`LocalStorageBackend` implemented,
  `S3StorageBackend` stubbed), with a type/size allow-list currently limited
  to images (≤10MB) and PDF (≤50MB), used today only by the student
  Ask-a-Question upload flow.
- **Naming collision to resolve**: the existing `Lesson` model is *published
  student-facing content* (a Topic's video+notes page). The new feature's
  "lesson plan" is a teacher's day-to-day teaching document — a different
  concept entirely. New tables are named `lesson_plans`, never `lessons`.

## 2. Workspace / multi-tenant model

```
User (existing, unchanged)
  │
  └── organization_members (new)
         │              │
         ▼              ▼
   organizations   role: OWNER | ADMIN | TEACHER
   (new)
     kind: PERSONAL | SCHOOL
```

- **`organizations`**: `id, kind (personal|school), name, created_by_user_id,
  created_at`. A `PERSONAL` organization is auto-created for every user who
  registers as (or is later granted) a teacher — this is what makes an
  "individual teacher" and a "school teacher" the same code path, exactly as
  the brief's own diagram shows. A `SCHOOL` organization is created
  explicitly during the "School" onboarding option.
- **`organization_members`**: `id, organization_id, user_id, role (owner|
  admin|teacher), invited_by_user_id, joined_at`. `role` here is
  **organization-scoped**, not the existing global `User.role`. A user keeps
  their existing global `role` (student/teacher/admin) for the student
  platform and admin platform exactly as today; `organization_members.role`
  is a separate, additive concept that only exists for planner features.
- A user can belong to multiple organizations (their personal workspace +
  any number of schools), matching the brief's diagram exactly.
- **Every planner table** (`classes`, `lesson_plans`, `resources`, etc.)
  carries an `organization_id` foreign key. Every planner query is filtered
  by `organization_id` server-side — never inferred from a client-supplied
  value, always derived from the authenticated user's verified membership.

## 3. Onboarding flow

Registration gets a third top-level choice alongside the existing
student/teacher radio (`RegisterRequest.role` already exists and already
blocks self-registered admins):

```
Register as:
  ○ Student            → existing flow, unchanged
  ○ Individual Teacher  → existing role=teacher flow + auto-create PERSONAL org
  ○ School              → role=teacher + create a new SCHOOL org, caller becomes OWNER
```

"Individual Teacher" is *not* a new role — it's today's existing
`role=teacher` registration, just also given a personal organization. This
means the existing `TeacherProfile`/`TeacherSubject` machinery for the
student-content-authoring side is completely untouched by this feature.

## 4. Permission model

Two independent, non-overlapping permission systems will coexist:

1. **Existing global-role system** (unchanged): `student`/`teacher`/`admin`,
   governs the student platform and the platform admin dashboard exactly as
   it does today.
2. **New organization-role system**: `owner`/`admin`/`teacher` within an
   `organization_members` row, governs everything under the planner
   (`classes`, `lesson_plans`, `resources`, `weekly_plans`). A School Admin
   is `organization_members.role = admin` in that one organization — it is
   **not** a value in the global `UserRole` enum, and grants no permissions
   in any other organization or on the student platform.

Rules enforced server-side (never UI-only), mirroring the brief's explicit
requirement:

- A school admin can view teacher lesson plans/activity within their own
  school, but cannot edit a teacher's lesson plan, create a teacher's
  classes, or read a teacher's *personal* (non-school) workspace.
- A teacher's personal workspace is invisible to every organization they
  also belong to, including one where they're a member.
- Cross-organization access is always denied, checked by an
  `assert_org_member(db, user, organization_id, min_role=...)` service
  function — the direct descendant of today's `assert_can_manage_subject`.

## 5. Data model (new tables)

Adapted to existing naming/PK/timestamp conventions (`UUIDPKMixin`,
`TimestampMixin`, snake_case tables, Postgres-native `UUID`/`Enum`):

```
organizations            id, kind, name, created_by_user_id
organization_members     id, organization_id, user_id, role, invited_by_user_id, joined_at
classes                  id, organization_id, teacher_user_id, name, subject_id (FK to
                          existing Subject, nullable), exam_board_id (FK, nullable),
                          qualification, year_group, created_at
lesson_plans             id, organization_id, class_id, teacher_user_id, title,
                          topic, duration_minutes, template_type, status (draft|
                          published), current_version_id, created_at, updated_at
lesson_plan_versions     id, lesson_plan_id, version_number, content (JSONB —
                          structured sections, see §6), created_by_user_id, created_at
resources                id, organization_id, uploaded_by_user_id, file_name,
                          storage_key, resource_type, exam_board, qualification,
                          subject_id (nullable FK), year_group, topic, unit,
                          source, extracted_text_status, created_at
resource_chunks          id, resource_id, chunk_index, text, metadata (JSONB),
                          embedding (nullable, only if/when pgvector lands — see §9)
weekly_plans             id, organization_id, class_id, week_start_date, created_at
weekly_plan_items        id, weekly_plan_id, lesson_plan_id (nullable until
                          scheduled), day_of_week, start_time, duration_minutes
worksheets                id, lesson_plan_id, title, content (JSONB), answer_key (JSONB)
homework                 id, lesson_plan_id, title, content (JSONB), answer_key
                          (JSONB), due_date, estimated_minutes
activity_logs            id, organization_id, user_id, action, target_type,
                          target_id, created_at
usage_records            id, organization_id, user_id, provider, model,
                          input_tokens, output_tokens, estimated_cost_cents,
                          created_at
```

`lesson_plan_versions.content` is structured JSON (Pydantic-validated on
write), not one text blob — matching the brief's explicit requirement and
the existing `Note.content_blocks` precedent (structured JSON list) already
in this codebase.

## 6. Lesson plan content shape (structured, not a text blob)

A Pydantic model tree, versioned as a whole document per save:

```python
class LessonSection(BaseModel):
    id: str                 # stable id, so drag-reorder doesn't lose identity
    type: str                # "starter" | "teacher_input" | "guided_practice" | ...
    title: str
    duration_minutes: int
    body: list[ContentBlock] # reuses the existing NoteBlocks block-type union
                              # (heading/paragraph/formula/key_point/example/exam_tip)
                              # extended with a couple of planner-specific block
                              # types (e.g. "activity_instruction")

class LessonPlanContent(BaseModel):
    learning_objectives: list[str]
    success_criteria: list[str] = []
    prior_knowledge: list[str] = []
    key_vocabulary: list[str] = []
    sections: list[LessonSection]
    differentiation: DifferentiationNotes | None = None
    assessment_for_learning: list[str] = []
    misconceptions: list[str] = []
    resources: list[ResourceRef] = []
    homework_id: UUID | None = None
    worksheet_id: UUID | None = None
    teacher_notes: str | None = None
    safeguarding_note: str | None = None   # populated only when the local
                                            # validator flags a sensitive topic
```

Not every section appears in every lesson — the local planning engine (§7)
decides which sections a given subject/age/duration warrants, then the
teacher can add/remove/reorder freely in the editor.

## 7. Local-first planning engine (no LLM by default)

A new `app/planning/` package, pure Python, no network calls:

- `templates.py` — the fixed lesson templates from the brief (Standard,
  Practical, Revision, Exam Prep, New Topic, Retrieval, Assessment, Review,
  Double, Short), each a `LessonSection` skeleton with default durations.
- `timing.py` — duration-sum validation exactly like the brief's worked
  example (50-minute lesson, sections summing to 45 → flag the 5-minute gap
  and suggest which section to extend). Pure arithmetic, no AI.
- `curriculum_matching.py` — given `(subject_id, exam_board_id, topic)`,
  looks up matching `resources`/existing `Question`/`Topic` rows as the
  "source of truth" the brief requires — the planner fills gaps from this
  before ever considering AI text.
- `worksheet_builder.py` / `homework_builder.py` — deterministic assembly
  from a question bank (reusing the existing `Question`/`QuestionOption`
  models — a worksheet is a curated, ordered subset of Questions, not new
  content, with an auto-generated answer key from the already-existing
  `correct_answer`/`explanation`/`is_correct` option fields).
- `weekly_planner.py` — schedule-gap/overload/repeated-topic/missing-
  assessment detection, pure Python over `weekly_plan_items`.
- `validator.py` — the pre-display lesson-quality checklist from the brief
  (durations sum correctly, objectives exist, assessment exists where
  expected, year group/subject/topic consistency).

This package must be independently useful and independently testable with
zero AI involved — Phase 4 explicitly ships before Phase 6 (AI) for exactly
this reason.

## 8. Tenant isolation: RLS decision

The brief asks for "PostgreSQL/Supabase Row Level Security where
appropriate." Since there's no Supabase, the real choice is between:

- **(A) Native Postgres RLS** on the new planner tables: policies keyed off
  a session variable (`SET app.current_user_id`) set per request. Real
  defense-in-depth (protects even against an application bug), but genuinely
  new operational machinery for this codebase — connection-pooling and the
  ORM session lifecycle both need to reliably set that variable on every
  request, and it only protects the new tables, so the app would end up with
  two different isolation mechanisms side by side.
- **(B) Extend the existing app-layer pattern**: every planner service
  function takes the authenticated user, resolves their verified
  `organization_members` row(s), and filters every query by
  `organization_id` from that — the direct extension of
  `assert_can_manage_subject`/`teacher_subject_ids` that the rest of this
  codebase already uses everywhere, tested the same way (the security
  test suite already asserts IDOR is blocked this way for existing
  features).

**My recommendation is (B)**, for consistency (one isolation mechanism
across the whole codebase, not two) and because it's directly testable with
the existing pytest pattern. (A) is a legitimate, more defense-in-depth
choice — this is called out explicitly as a decision for you, not something
I'll pick silently.

## 9. Resource ingestion pipeline

```
Upload (PDF/DOCX/TXT via existing StorageBackend, allow-list extended)
  → text extraction (pypdf for PDF, python-docx for DOCX, plain read for TXT)
  → cleaning (whitespace/header-footer stripping)
  → section detection (heading heuristics)
  → chunking (size-bounded, section-aware)
  → metadata (exam_board, qualification, subject_id, year_group, topic, unit,
    resource_type, source, organization_id — from a small teacher-filled
    form at upload time, not inferred)
  → store (resources + resource_chunks rows)
```

No Pinecone/Weaviate/Elasticsearch. If semantic search over resources proves
necessary, it's the `pgvector` Postgres extension on the existing database
(a nullable `embedding` column on `resource_chunks`, populated lazily) —
deferred to Phase 5/6, not built speculatively now. Keyword/metadata
filtering (subject/exam-board/topic/year-group) covers curriculum-matching
without any vector search at all, and ships first.

## 10. AI provider abstraction

```python
class AIProvider(ABC):
    @abstractmethod
    async def generate_structured(self, prompt: str, schema: type[BaseModel],
                                   context: dict) -> BaseModel: ...
```

- One structured call per lesson-plan generation (never N calls for N
  sections), per the brief's cost-control requirement.
- `usage_records` logs every call (provider, model, tokens, estimated cost,
  user, organization) — surfaced later in the school/teacher dashboard.
- The uploaded/approved curriculum resource is always passed as authoritative
  context; the AI is prompted to fill gaps and improve wording, never to
  invent curriculum requirements the resource already specifies.
- **Safeguarding rule, enforced in the abstraction itself, not left to
  prompting**: any lesson-plan content flagged by the local validator as
  safeguarding-sensitive is never sent to the AI provider for rewriting —
  the teacher edits that section manually, and the system surfaces the
  standard "follow your school's DSL procedure" note instead of an AI
  suggestion.
- Provider is swappable via config (mirrors the existing `STORAGE_BACKEND`
  swap pattern) — no code outside the abstraction references a specific
  vendor SDK.

## 11. Export

`reportlab` (PDF) and `python-docx` (DOCX) — both new backend dependencies,
neither currently installed. A `lesson_plan_versions.content` document,
`worksheets.content`, and `homework.content` all render through the same
export service, since they share the structured-block shape.

## 12. Frontend structure (new, additive)

A new top-level route group, entirely separate from existing student routes:

```
/planner
  /planner/onboarding          (Student / Individual Teacher / School choice)
  /planner/[orgId]/dashboard   (teacher dashboard, or school dashboard by org kind)
  /planner/[orgId]/classes
  /planner/[orgId]/classes/[classId]
  /planner/[orgId]/lesson-plans
  /planner/[orgId]/lesson-plans/[id]      (the structured editor)
  /planner/[orgId]/weekly
  /planner/[orgId]/resources
  /planner/[orgId]/school                  (school-admin-only: teachers, curriculum, activity)
  /planner/[orgId]/settings
```

A workspace switcher (new shared component — the first shared nav component
this codebase will have) lets a user move between their personal workspace
and any school they belong to; the `[orgId]` in the URL is always
re-verified server-side against the caller's `organization_members`, never
trusted from the URL alone.

New frontend dependency: a drag-and-drop library (e.g. `@dnd-kit/core`) for
section reordering and the weekly calendar — nothing currently in
`package.json` covers this.

## 13. Migration strategy

This feature starts proper incremental Alembic migrations (one per
phase/table-group) rather than continuing the single-big-migration pattern
used so far. Every migration is additive-only in Phase 1–3 (new tables, no
changes to existing tables) — the existing 45+ tables are not touched.

## 14. Safeguarding posture (product, not just security)

- The system never states or implies legal compliance with UK safeguarding
  law — every safeguarding-adjacent surface carries a standing note that the
  school remains responsible for its own policy, DSL procedures, and staff
  training.
- No AI "safeguarding decision maker" — the local validator can *flag* a
  topic as safeguarding-sensitive (a fixed keyword/topic list, not an LLM
  judgment call) and surface the standard escalation note; it never
  instructs a teacher to ignore or de-escalate a concern.
- Lesson plans and worksheets never require or store individual student
  identifying/medical/SEND-diagnostic information — differentiation fields
  are teacher-authored free text (e.g. "core/support/challenge" tiering),
  never a system-inferred diagnosis.

## 15. Explicit open decisions (need your call before Phase 1)

1. **RLS approach** (§8): extend the existing app-layer isolation pattern
   (recommended, consistent with the rest of the codebase), or introduce
   native Postgres RLS as a second, additional isolation mechanism.
2. **Organization role naming**: `owner/admin/teacher` as proposed, or
   different labels to match how you want school staff to see themselves in
   the UI (e.g. "Head of Department" as an intermediate role) — easy to
   change now, harder once permission checks are written against it.
3. **Personal-workspace auto-creation**: should this also retroactively
   create a `PERSONAL` organization for the 1-2 existing teacher accounts in
   the dev database (harmless, additive), or only for newly-registered
   teachers from this point forward?
4. **DnD library choice** for the frontend (I'd default to `@dnd-kit/core`
   unless you have a preference) — first new frontend runtime dependency
   since the project was scaffolded.

## 16. Phased delivery (mirrors the brief's own phase list)

Phase 0 (this doc) → Phase 1 (organizations/membership/onboarding, fully
tested in isolation) → Phase 2 (classes) → Phase 3 (lesson plan CRUD +
structured editor, **no AI**) → Phase 4 (local planning engine) → Phase 5
(resource ingestion) → Phase 6 (optional AI, additive only) → Phase 7
(worksheets/homework) → Phase 8 (weekly planner) → Phase 9 (school admin) →
Phase 10 (export/polish). Each phase ends with: tests run, typecheck/lint
run, migrations verified, existing student and teacher functionality
manually re-verified, and a report of exactly what changed — before moving
to the next phase.
