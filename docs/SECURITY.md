# Acadex — Security Review (Milestone 12)

A review pass over the codebase built through Milestone 11, plus the fixes it
produced. Re-run the checks below whenever new endpoints are added.

## What was checked

- **SQL injection** — every query goes through SQLAlchemy's ORM/query builder;
  no raw SQL or string-formatted queries anywhere in `app/`.
- **Auth on mutating routes** — verified with an AST-based script (not just
  grep) that every `POST`/`PUT`/`PATCH`/`DELETE` route depends on
  `require_*` or `get_current_user`, with two intentional exceptions:
  `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/password-reset/*`
  (must work for logged-out users) and `POST /questions/{id}/check`
  (deliberately public instant practice-check, no student data involved).
- **IDOR / ownership checks** — covered by the automated test suite:
  students can't see each other's dashboards, can't mark someone else's
  notification read, can't edit/delete another student's comment; teachers
  can only manage content in subjects they're assigned to (`TeacherSubject`);
  a course-students view is scoped to the requesting teacher's own courses.
- **Password handling** — bcrypt via the `bcrypt` package directly (not
  passlib, whose bundled self-test breaks on bcrypt ≥ 4 — see Milestone 2);
  72-byte length enforced before hashing instead of silently truncating.
- **JWT** — HS256 only, `algorithms=[...]` pinned on decode (no algorithm-
  confusion surface), separate access/refresh/password-reset token purposes
  checked explicitly so one can't be used as another.
- **Password reset** — token carries a fingerprint of the current password
  hash, so it's rejected after the password changes; the request endpoint
  never reveals whether an email is registered.
- **Rate limiting** — register/login/password-reset are limited (slowapi) to
  blunt credential-stuffing and enumeration attempts.
- **File uploads** — type allowlist and size limits enforced in
  `app/storage/base.py` before anything touches disk; stored filenames are
  server-generated UUIDs (only the extension survives from the original
  name), which also closes off path traversal via a crafted filename.
- **CORS** — `allow_origins` is the configured frontend origin list, not `*`.
- **Secrets** — no secrets committed; `SECRET_KEY` has a placeholder default
  that only works in `ENVIRONMENT=development`. Starting the app with
  `ENVIRONMENT=production` and the placeholder still set now fails fast at
  import time (`app/main.py`) instead of silently signing tokens with a
  public, guessable key.
- **Dependency versions** — `python-multipart` was pinned to 0.0.9 (a ReDoS
  fix landed in 0.0.18) despite being on the file-upload path; bumped to
  0.0.18. `python-jose` bumped to the latest 3.x patch. Left FastAPI/
  SQLAlchemy/Pydantic on their tested pins rather than jumping several minor
  versions this late without re-testing every milestone against the new
  versions — flagged as a follow-up, not done blindly.

## Automated regression coverage

`backend/tests/` (pytest, run against a real Postgres `acadex_test` database,
each test wrapped in a rolled-back transaction) covers:

- `test_auth.py` — register/login, duplicate email, wrong password, admin
  self-registration block, password reset token lifecycle.
- `test_education.py` — RBAC on subject/course creation, teacher subject
  scoping, duplicate slug rejection, unpublished-course visibility.
- `test_learning.py` — enrollment (including idempotent re-enroll and the
  "can't enroll in an unpublished course" guard), progress completion
  boundaries, bookmarks, dashboard data isolation between students.
- `test_quiz.py` — MCQ/numerical auto-marking, full quiz scoring, duplicate
  submission rejection, answer keys never leaking through the safe view.
- `test_community.py` — comment reply nesting, edit/delete ownership,
  soft-delete keeping thread shape, vote toggling, unauthenticated block.
- `test_admin.py` — stats accuracy, self-deactivation block, deactivated
  users rejected at login, teacher verify + subject assignment (and that
  assignment — not verification — is what actually grants access).

Run with:

```bash
createdb acadex_test   # once
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Known follow-ups (not blocking MVP)

- List endpoints (`/admin/users`, `/questions`, etc.) are unbounded — fine at
  MVP scale, but should get real pagination before the user base grows past
  a few thousand rows per table.
- Framework-level dependency versions (FastAPI, SQLAlchemy, Pydantic) should
  be revisited and bumped deliberately, with the full test suite re-run,
  rather than pinned indefinitely.
