# Acadex — Milestone Plan

1. **Project architecture** ✅ — frontend/backend/database scaffolding, env
   config, docs.
2. **Authentication** ✅ — student/teacher/admin register, login, logout,
   password reset, role-based access.
3. **Education structure** ✅ — CRUD + browsing for levels, exam boards,
   subjects, courses, chapters, topics, lessons.
4. **Student experience** ✅ — dashboard, enrollment, progress, bookmarks.
5. **Video + notes** ✅ — lesson player, resume tracking, rich notes
   rendering (KaTeX-rendered formulas, callouts).
6. **Practice questions + quizzes** ✅ — question bank, quiz taking,
   auto-marking (MCQ/true-false/numerical; short-answer/structured are
   recorded but left for human/future-AI marking).
7. **Question upload + discussions** ✅ — Ask-a-Question with image upload,
   comments, nested replies, votes, teacher pin/verify, reports.
8. **Teacher dashboard** ✅ — content authoring, publish toggles, student
   progress views.
9. **Admin dashboard** ✅ — user/teacher management, platform stats, report
   moderation.
10. **Past-paper / resource library** ✅ — browse + admin authoring of
    metadata (no scraped content — resources are official links or
    properly licensed material only).
11. **Search + notifications** ✅ — global search across subjects/courses/
    lessons/past papers; in-app notifications for replies and teacher
    answers.
12. **Testing + security + performance pass** ✅ — pytest suite (36 tests)
    covering RBAC/IDOR/auto-marking/ownership, a documented security review
    (`docs/SECURITY.md`), two real vulnerabilities fixed along the way.
13. **Deployment** ✅ — runbook in `docs/DEPLOYMENT.md` (Railway/Render +
    Vercel, env var checklist, migration/seed steps). No live environment
    provisioned — that needs real cloud credentials this repo doesn't have.

**Future (post-MVP):** live classes, payments/subscriptions, AI tutor — schema is
in place from Milestone 1 (see `docs/DATABASE_SCHEMA.md`), but no routes/UI ship
until explicitly prioritized.
