"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type {
  ActivityLogRow,
  CurriculumSubject,
  Organization,
  OrganizationMember,
  OrganizationRole,
  TeacherOverviewRow,
  WeeklyPlanDetail,
} from "@/types";

type Tab = "teachers" | "curriculum" | "activity";

function isoDate(d: Date): string {
  // Local date, not UTC (toISOString() would shift the date for users
  // behind UTC) -- see the identical helper/comment in the weekly planner page.
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function mondayOf(d: Date): Date {
  const copy = new Date(d);
  const day = (copy.getDay() + 6) % 7;
  copy.setDate(copy.getDate() - day);
  return copy;
}

export default function SchoolAdminPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const router = useRouter();
  const { user, loading } = useAuth();

  const [myRole, setMyRole] = useState<OrganizationRole | null>(null);
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [tab, setTab] = useState<Tab>("teachers");

  useEffect(() => {
    if (!loading && (!user || user.role !== "teacher")) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user || user.role !== "teacher" || !orgId) return;
    apiFetch<Organization[]>("/organizations/me", undefined, true)
      .then((orgs) => {
        const mine = orgs.find((o) => o.id === orgId);
        if (!mine || (mine.my_role !== "owner" && mine.my_role !== "admin")) {
          router.replace("/planner");
          return;
        }
        setMyRole(mine.my_role);
      })
      .finally(() => setCheckingAccess(false));
  }, [user, orgId, router]);

  if (loading || !user || checkingAccess || !myRole) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <Link href="/planner" className="text-sm font-medium text-brand-700 hover:underline">
        ← Your workspaces
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-slate-900">School admin</h1>
      <p className="mt-1 text-sm text-slate-600">
        Manage teachers, your school&apos;s standard subject list, and see what&apos;s been happening across the workspace.
      </p>

      <div className="mt-6 flex gap-2 border-b border-slate-200">
        {(["teachers", "curriculum", "activity"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium capitalize ${
              tab === t ? "border-b-2 border-brand-600 text-brand-700" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "teachers" && <TeachersTab orgId={orgId} myRole={myRole} />}
        {tab === "curriculum" && <CurriculumTab orgId={orgId} />}
        {tab === "activity" && <ActivityTab orgId={orgId} />}
      </div>
    </main>
  );
}

function TeachersTab({ orgId, myRole }: { orgId: string; myRole: OrganizationRole }) {
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [overview, setOverview] = useState<TeacherOverviewRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<OrganizationRole>("teacher");
  const [formError, setFormError] = useState<string | null>(null);

  const [selectedTeacher, setSelectedTeacher] = useState<string>("");
  const [weekStart, setWeekStart] = useState(() => isoDate(mondayOf(new Date())));
  const [weekPlan, setWeekPlan] = useState<WeeklyPlanDetail | null>(null);
  const [weekError, setWeekError] = useState<string | null>(null);

  function load() {
    apiFetch<OrganizationMember[]>(`/organizations/${orgId}/members`, undefined, true).then(setMembers).catch(() => {});
    apiFetch<TeacherOverviewRow[]>(`/organizations/${orgId}/teacher-overview`, undefined, true)
      .then((rows) => {
        setOverview(rows);
        if (rows.length > 0) setSelectedTeacher((prev) => prev || rows[0].user_id);
      })
      .catch(() => {});
  }

  useEffect(load, [orgId]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    try {
      await apiFetch(
        `/organizations/${orgId}/members`,
        { method: "POST", body: JSON.stringify({ email, role }) },
        true
      );
      setEmail("");
      load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Couldn't add that teacher.");
    }
  }

  async function handleRoleChange(memberId: string, newRole: OrganizationRole) {
    setError(null);
    try {
      await apiFetch(`/organizations/${orgId}/members/${memberId}`, { method: "PATCH", body: JSON.stringify({ role: newRole }) }, true);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't change that role.");
    }
  }

  async function handleRemove(memberId: string) {
    setError(null);
    try {
      await apiFetch(`/organizations/${orgId}/members/${memberId}`, { method: "DELETE" }, true);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't remove that member.");
    }
  }

  async function handleViewWeek() {
    setWeekError(null);
    setWeekPlan(null);
    try {
      const plan = await apiFetch<WeeklyPlanDetail>(
        `/organizations/${orgId}/weekly-overview?teacher_user_id=${selectedTeacher}&week_start_date=${weekStart}`,
        undefined,
        true
      );
      setWeekPlan(plan);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setWeekError("Nothing planned by this teacher for that week.");
      } else {
        setWeekError(err instanceof ApiError ? err.message : "Couldn't load that week.");
      }
    }
  }

  return (
    <div className="flex flex-col gap-8">
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div>
        <h2 className="text-lg font-semibold text-slate-900">Members</h2>
        <div className="mt-3 flex flex-col gap-2">
          {members.map((m) => {
            const stats = overview.find((o) => o.user_id === m.user_id);
            return (
              <div key={m.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3 text-sm">
                <div>
                  <p className="font-medium text-slate-900">{m.display_name}</p>
                  <p className="text-xs text-slate-500">
                    {m.email} {stats && `· ${stats.class_count} classes · ${stats.lesson_plan_count} lesson plans`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={m.role}
                    onChange={(e) => handleRoleChange(m.id, e.target.value as OrganizationRole)}
                    className="rounded border border-slate-300 px-2 py-1 text-xs"
                  >
                    <option value="teacher">teacher</option>
                    <option value="admin">admin</option>
                    <option value="owner">owner</option>
                  </select>
                  <button onClick={() => handleRemove(m.id)} className="text-xs font-medium text-red-600 hover:underline">
                    Remove
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <form onSubmit={handleAdd} className="mt-4 flex flex-wrap items-end gap-2">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Teacher email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value as OrganizationRole)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="teacher">teacher</option>
              <option value="admin">admin</option>
              {myRole === "owner" && <option value="owner">owner</option>}
            </select>
          </div>
          <Button type="submit" className="text-sm">
            Add member
          </Button>
        </form>
        {formError && <p className="mt-2 text-sm text-red-600">{formError}</p>}
      </div>

      <div className="border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-slate-900">A teacher&apos;s weekly plan (read-only)</h2>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Teacher</label>
            <select value={selectedTeacher} onChange={(e) => setSelectedTeacher(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              {overview.map((o) => (
                <option key={o.user_id} value={o.user_id}>
                  {o.display_name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-700">Week starting</label>
            <input type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <Button variant="secondary" className="text-sm" onClick={handleViewWeek}>
            View week
          </Button>
        </div>

        {weekError && <p className="mt-3 text-sm text-slate-500">{weekError}</p>}
        {weekPlan && (
          <div className="mt-4 flex flex-col gap-2">
            {weekPlan.items.length === 0 && <p className="text-sm text-slate-400">No sessions scheduled that week.</p>}
            {weekPlan.items.map((item) => (
              <div key={item.id} className="rounded-lg border border-slate-100 bg-slate-50 p-2 text-xs">
                <span className="font-medium capitalize">{item.day_of_week}</span> {item.start_time.slice(0, 5)} ·{" "}
                {item.class_name} · {item.duration_minutes} min {item.topic && `· ${item.topic}`}
              </div>
            ))}
            {weekPlan.issues.map((issue, i) => (
              <p key={i} className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                {issue.message}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function CurriculumTab({ orgId }: { orgId: string }) {
  const [subjects, setSubjects] = useState<CurriculumSubject[]>([]);
  const [name, setName] = useState("");
  const [keyStage, setKeyStage] = useState("");
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch<CurriculumSubject[]>(`/organizations/${orgId}/curriculum-subjects`, undefined, true).then(setSubjects).catch(() => {});
  }

  useEffect(load, [orgId]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiFetch(
        `/organizations/${orgId}/curriculum-subjects`,
        { method: "POST", body: JSON.stringify({ name, key_stage: keyStage || null }) },
        true
      );
      setName("");
      setKeyStage("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add that subject.");
    }
  }

  async function handleDelete(id: string) {
    await apiFetch(`/organizations/${orgId}/curriculum-subjects/${id}`, { method: "DELETE" }, true);
    load();
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900">Standard subject list</h2>
      <p className="mt-1 text-sm text-slate-500">
        A shared reference so teachers creating classes converge on the same subject names.
      </p>

      <div className="mt-4 flex flex-col gap-2">
        {subjects.map((s) => (
          <div key={s.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3 text-sm">
            <span>
              {s.name} {s.key_stage && <span className="text-xs text-slate-500">· {s.key_stage}</span>}
            </span>
            <button onClick={() => handleDelete(s.id)} className="text-xs font-medium text-red-600 hover:underline">
              Delete
            </button>
          </div>
        ))}
        {subjects.length === 0 && <p className="text-sm text-slate-400">No subjects added yet.</p>}
      </div>

      <form onSubmit={handleAdd} className="mt-4 flex flex-wrap items-end gap-2">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-slate-700">Subject name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-slate-700">Key stage (optional)</label>
          <input value={keyStage} onChange={(e) => setKeyStage(e.target.value)} placeholder="e.g. KS2" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <Button type="submit" className="text-sm">
          Add subject
        </Button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}

function ActivityTab({ orgId }: { orgId: string }) {
  const [activity, setActivity] = useState<ActivityLogRow[]>([]);

  useEffect(() => {
    apiFetch<ActivityLogRow[]>(`/organizations/${orgId}/activity`, undefined, true).then(setActivity).catch(() => {});
  }, [orgId]);

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900">Recent activity</h2>
      <div className="mt-4 flex flex-col gap-2">
        {activity.map((a) => (
          <div key={a.id} className="rounded-lg border border-slate-200 p-3 text-sm">
            <span className="font-medium text-slate-900">{a.actor_name}</span>{" "}
            <span className="text-slate-600">{a.action.replace(".", " ")}</span> — {a.summary}
            <span className="ml-2 text-xs text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
          </div>
        ))}
        {activity.length === 0 && <p className="text-sm text-slate-400">Nothing yet.</p>}
      </div>
    </div>
  );
}
