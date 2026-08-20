"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AdminReportRow, AdminUserRow, PlatformStats, Subject, TeacherRow } from "@/types";

const STAT_LABELS: [keyof PlatformStats, string][] = [
  ["total_users", "Total users"],
  ["total_students", "Students"],
  ["total_teachers", "Teachers"],
  ["total_subjects", "Subjects"],
  ["total_courses", "Courses"],
  ["total_published_courses", "Published courses"],
  ["total_lessons", "Lessons"],
  ["total_questions", "Questions"],
  ["total_quiz_attempts", "Quiz attempts"],
  ["total_discussions", "Discussions"],
  ["total_question_threads", "Ask-a-question threads"],
  ["pending_reports", "Pending reports"],
];

export default function AdminDashboardPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [teachers, setTeachers] = useState<TeacherRow[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [reports, setReports] = useState<AdminReportRow[]>([]);
  const [assignSubjectId, setAssignSubjectId] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) router.replace("/dashboard");
  }, [loading, user, router]);

  async function loadAll() {
    const [s, u, t, subj, r] = await Promise.all([
      apiFetch<PlatformStats>("/admin/stats", undefined, true),
      apiFetch<AdminUserRow[]>("/admin/users", undefined, true),
      apiFetch<TeacherRow[]>("/admin/teachers", undefined, true),
      apiFetch<Subject[]>("/subjects"),
      apiFetch<AdminReportRow[]>("/admin/reports?status_filter=pending", undefined, true),
    ]);
    setStats(s);
    setUsers(u);
    setTeachers(t);
    setSubjects(subj);
    setReports(r);
  }

  useEffect(() => {
    async function init() {
      if (user?.role === "admin") await loadAll();
    }
    init();
  }, [user]);

  async function toggleActive(row: AdminUserRow) {
    await apiFetch(`/admin/users/${row.id}/active`, { method: "PATCH", body: JSON.stringify({ is_active: !row.is_active }) }, true);
    loadAll();
  }

  async function toggleVerify(teacher: TeacherRow) {
    await apiFetch(
      `/admin/teachers/${teacher.id}/verify`,
      { method: "PATCH", body: JSON.stringify({ is_verified_teacher: !teacher.is_verified_teacher }) },
      true
    );
    loadAll();
  }

  async function assignSubject(teacher: TeacherRow) {
    const subjectId = assignSubjectId[teacher.id];
    if (!subjectId) return;
    await apiFetch(`/admin/teachers/${teacher.id}/subjects`, { method: "POST", body: JSON.stringify({ subject_id: subjectId }) }, true);
    loadAll();
  }

  async function unassignSubject(teacher: TeacherRow, subjectId: string) {
    await apiFetch(`/admin/teachers/${teacher.id}/subjects/${subjectId}`, { method: "DELETE" }, true);
    loadAll();
  }

  async function resolveReport(reportId: string) {
    await apiFetch(`/reports/${reportId}/resolve`, { method: "PUT" }, true);
    loadAll();
  }

  if (loading || !user || !stats) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Admin dashboard</h1>
        <Link href="/admin/past-papers" className="text-sm font-medium text-brand-700 hover:underline">
          Manage past papers →
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {STAT_LABELS.map(([key, label]) => (
          <div key={key} className="rounded-xl border border-slate-200 p-4">
            <p className="text-2xl font-bold text-slate-900">{stats[key]}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">Users</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-2">Name</th>
                <th className="pb-2">Email</th>
                <th className="pb-2">Role</th>
                <th className="pb-2">Status</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {users.map((row) => (
                <tr key={row.id} className="border-b border-slate-100">
                  <td className="py-2">{row.display_name}</td>
                  <td className="py-2 text-slate-500">{row.email}</td>
                  <td className="py-2 capitalize">{row.role}</td>
                  <td className="py-2">{row.is_active ? "Active" : "Deactivated"}</td>
                  <td className="py-2">
                    <button onClick={() => toggleActive(row)} className="text-xs font-medium text-brand-700 hover:underline">
                      {row.is_active ? "Deactivate" : "Reactivate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">Teachers</h2>
        <div className="mt-4 flex flex-col gap-4">
          {teachers.map((teacher) => (
            <div key={teacher.id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex items-center justify-between">
                <p className="font-medium text-slate-900">
                  {teacher.display_name}{" "}
                  {teacher.is_verified_teacher && (
                    <span className="ml-2 rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">
                      Verified
                    </span>
                  )}
                </p>
                <button onClick={() => toggleVerify(teacher)} className="text-xs font-medium text-brand-700 hover:underline">
                  {teacher.is_verified_teacher ? "Unverify" : "Verify teacher"}
                </button>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {teacher.subjects.map((s) => (
                  <span key={s.id} className="flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">
                    {s.name}
                    <button onClick={() => unassignSubject(teacher, s.id)} className="text-slate-400 hover:text-red-600">
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div className="mt-3 flex gap-2">
                <select
                  value={assignSubjectId[teacher.id] ?? ""}
                  onChange={(e) => setAssignSubjectId((prev) => ({ ...prev, [teacher.id]: e.target.value }))}
                  className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs"
                >
                  <option value="">Assign subject…</option>
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => assignSubject(teacher)}
                  className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-900"
                >
                  Assign
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">Pending reports</h2>
        {reports.length === 0 ? (
          <p className="mt-4 text-sm text-slate-500">No pending reports.</p>
        ) : (
          <div className="mt-4 flex flex-col gap-3">
            {reports.map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-4 text-sm">
                <div>
                  <p className="font-medium text-slate-900 capitalize">{r.target_type.replace("_", " ")}</p>
                  <p className="text-slate-600">{r.reason}</p>
                </div>
                <button onClick={() => resolveReport(r.id)} className="text-xs font-medium text-brand-700 hover:underline">
                  Resolve
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
