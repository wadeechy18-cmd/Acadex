# Acadex — Database Schema (Milestone 1)

PostgreSQL, accessed through SQLAlchemy models in `backend/app/models/`, versioned
via Alembic migrations in `backend/alembic/versions/`. Primary keys are UUIDs.
Every table has `created_at` / `updated_at` timestamps via a shared mixin.

Tables marked **(future)** exist now so later milestones are additive, but have no
API routes or UI yet.

## Identity

- **User** — email, hashed_password, role (`student`/`teacher`/`admin`), is_active,
  is_verified.
- **StudentProfile** — 1:1 with User. education_level, exam_board preference,
  display_name, avatar.
- **TeacherProfile** — 1:1 with User. bio, qualifications, is_verified_teacher,
  subjects taught (M2M via `TeacherSubject`).
- **AdminProfile** — 1:1 with User. permissions scope (future fine-grained roles).

## Learning hierarchy

`EducationLevel → ExamBoard → Subject → Course → Chapter → Topic → Lesson`

- **EducationLevel** — e.g. GCSE, IGCSE, International A-Level, University Year 1.
- **ExamBoard** — e.g. Edexcel, Cambridge, OxfordAQA. Nullable link to
  EducationLevel (university content has no exam board).
- **Subject** — belongs to EducationLevel (+ optional ExamBoard). e.g. Mathematics.
- **Course** — belongs to Subject. A subject can have multiple courses/specs.
- **Chapter** — belongs to Course, ordered (`order_index`).
- **Topic** — belongs to Chapter, ordered.
- **Lesson** — belongs to Topic, ordered, `lesson_type` (video/notes/mixed).

## Content

- **Video** — 1:1/1:N with Lesson. Stores `provider`, `external_id`/`storage_key`,
  duration_seconds, thumbnail_key — never a raw hard-coded URL.
- **Note** — belongs to Topic/Lesson. Rich content stored as structured JSON/HTML
  blocks (headings, formulas, images, tables) rendered client-side.

## Assessment

- **Question** — subject/exam board/level/chapter/topic tags, difficulty,
  question_type (`mcq`/`short_answer`/`numerical`/`true_false`/`structured`),
  marks, prompt, explanation.
- **QuestionOption** — belongs to Question (for MCQ/true-false).
- **TopicTag** — M2M tag table so a Question/PastPaperQuestion can map to multiple
  topics/subtopics independent of the primary chapter/topic FK.
- **Quiz** — belongs to Topic or Chapter, has_timer, time_limit_seconds.
- **QuizQuestion** — M2M Quiz↔Question with order_index and marks override.
- **QuizAttempt** — belongs to Student + Quiz. score, percentage, started_at,
  submitted_at.
- **QuizAnswer** — belongs to QuizAttempt + Question. student's answer, is_correct.

## Student progress

- **Enrollment** — Student↔Course, enrolled_at, status.
- **Progress** — Student↔Topic (and rolled up to Chapter/Course in the API layer),
  completion_percentage, last_position_seconds (video resume), completed_at.
- **Bookmark** — Student↔Lesson/Question, polymorphic via `target_type`/`target_id`.
- **StudySession** — lightweight event log (student, topic, started_at, duration)
  used for "recently viewed" and future analytics/AI weakness detection.

## Community / Ask-a-Question

- **Discussion** — belongs to Topic (or standalone via QuestionThread). title,
  created_by.
- **Comment** — belongs to Discussion, self-referential `parent_comment_id` for
  replies, `is_verified_teacher_answer`, `is_pinned`.
- **QuestionThread** — the "Ask a Question" feature: student_id, subject_id,
  topic_id (nullable), description, status.
- **QuestionImage** — belongs to QuestionThread, storage_key,
  `ai_analysis` JSON **(future — nullable, unused until AI tutor ships)**.
- **Vote** — polymorphic upvote/downvote on Comment, unique per (user, target).
- **Report** — polymorphic content report (Comment/QuestionThread), reason, status,
  resolved_by.

## Past papers

- **PastPaper** — level/exam_board/subject/year/session/paper_number, title.
- **PastPaperResource** — belongs to PastPaper. resource_type
  (`official_link`/`licensed_document`/`original_solution`), url or storage_key.
  Only populated with content Acadex has the legal right to host or link to.
- **PastPaperQuestion** — belongs to PastPaper, links to Question for topic-tagged
  practice, question_number, marks.

## Notifications

- **Notification** — belongs to User, type, payload JSON, read_at. Delivery
  channel (in-app now; email/push are additive columns, unused in MVP).

## Future — Live classes **(future)**

- **LiveClass** — teacher_id, subject/topic, scheduled_at, duration_minutes,
  max_students, is_free, price_cents.
- **LiveClassEnrollment** — Student↔LiveClass.
- **LiveClassRecording** — belongs to LiveClass, storage_key.

## Future — Billing / entitlements **(future)**

- **Subscription** — Student↔plan, status, renews_at.
- **Payment** — payment provider reference, amount, status.
- **Purchase** — one-off purchase of a Course/LiveClass.
- **Entitlement** — the single source of truth the API checks before serving
  gated content: (user_id, resource_type, resource_id, granted_via, expires_at).
  In MVP, a middleware helper always returns "granted" for `is_free` content so no
  route needs an `if paid` branch yet.

## Future — AI **(future)**

- **AIConversation** — Student↔context (QuestionThread/Topic), started_at.
- **AIMessage** — belongs to AIConversation, role (`user`/`assistant`), content,
  linked QuestionImage where relevant.

## Indexing notes

- Foreign keys are indexed by default via SQLAlchemy relationship + explicit
  `index=True` on hot lookup columns (`user.email`, hierarchy FKs,
  `quiz_attempt.student_id`, `notification.user_id`, `discussion.topic_id`).
- Composite ordering columns (`order_index`) are used instead of relying on
  insertion order, so content can be reordered from the admin dashboard.
