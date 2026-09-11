"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { DAYS_OF_WEEK } from "@/types";
import type { DayOfWeek, LessonPlan, TeachingClass, WeeklyPlanDetail, WeeklyPlanIssue } from "@/types";

function isoDate(d: Date): string {
  // Deliberately NOT toISOString() -- that converts to UTC first, which can
  // shift the date by one day for any user behind UTC (e.g. late Sunday
  // evening in America/New_York already reads as Monday in UTC), sending
  // the wrong week_start_date to the API. Format the *local* date instead.
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function mondayOf(d: Date): Date {
  const copy = new Date(d);
  const day = (copy.getDay() + 6) % 7; // 0 = Monday
  copy.setDate(copy.getDate() - day);
  return copy;
}

function addDays(d: Date, days: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + days);
  return copy;
}

const SEVERITY_STYLE: Record<string, string> = {
  warning: "border-amber-300 bg-amber-50 text-amber-900",
  info: "border-slate-200 bg-slate-50 text-slate-700",
};

export default function WeeklyPlannerPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const router = useRouter();
  const { user, loading } = useAuth();

  const [weekStart, setWeekStart] = useState<Date>(() => mondayOf(new Date()));
  const [plan, setPlan] = useState<WeeklyPlanDetail | null>(null);
  const [classes, setClasses] = useState<TeachingClass[]>([]);
  const [lessonPlansByClass, setLessonPlansByClass] = useState<Record<string, LessonPlan[]>>({});
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [day, setDay] = useState<DayOfWeek>("monday");
  const [classId, setClassId] = useState("");
  const [lessonPlanId, setLessonPlanId] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [durationMinutes, setDurationMinutes] = useState(50);
  const [topicOverride, setTopicOverride] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!loading && (!user || user.role !== "teacher")) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user || user.role !== "teacher" || !orgId) return;
    apiFetch<TeachingClass[]>(`/organizations/${orgId}/classes`, undefined, true)
      .then((rows) => {
        setClasses(rows);
        if (rows.length > 0) setClassId((prev) => prev || rows[0].id);
      })
      .catch(() => {
        // Non-critical -- the "add session" form just shows no classes to pick.
      });
  }, [user, orgId]);

  useEffect(() => {
    if (!classId) return;
    apiFetch<LessonPlan[]>(`/classes/${classId}/lesson-plans`, undefined, true)
      .then((rows) => setLessonPlansByClass((prev) => ({ ...prev, [classId]: rows })))
      .catch(() => {
        // Non-critical -- linking a lesson plan to the slot is optional.
      });
  }, [classId]);

  function loadWeek(target: Date) {
    if (!user || user.role !== "teacher" || !orgId) return;
    setDataLoading(true);
    setError(null);
    setPlan(null);
    apiFetch<WeeklyPlanDetail>(`/organizations/${orgId}/weekly-plans?week_start_date=${isoDate(target)}`, undefined, true)
      .then(setPlan)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setPlan(null); // no plan yet for this week -- show "start planning this week"
        } else {
          setError(err instanceof ApiError ? err.message : "Couldn't load this week.");
        }
      })
      .finally(() => setDataLoading(false));
  }

  useEffect(() => {
    loadWeek(weekStart);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, orgId, weekStart]);

  async function handleStartPlanning() {
    const created = await apiFetch<WeeklyPlanDetail>(
      `/organizations/${orgId}/weekly-plans`,
      { method: "POST", body: JSON.stringify({ week_start_date: isoDate(weekStart) }) },
      true
    );
    setPlan(created);
  }

  async function handleAddItem(e: React.FormEvent) {
    e.preventDefault();
    if (!plan) return;
    setFormError(null);
    setCreating(true);
    try {
      await apiFetch(
        `/weekly-plans/${plan.id}/items`,
        {
          method: "POST",
          body: JSON.stringify({
            class_id: classId,
            lesson_plan_id: lessonPlanId || null,
            day_of_week: day,
            start_time: `${startTime}:00`,
            duration_minutes: durationMinutes,
            topic_override: lessonPlanId ? null : topicOverride || null,
          }),
        },
        true
      );
      setTopicOverride("");
      loadWeek(weekStart);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Couldn't add that session.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteItem(itemId: string) {
    await apiFetch(`/weekly-plan-items/${itemId}`, { method: "DELETE" }, true);
    loadWeek(weekStart);
  }

  if (loading || !user) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  const itemsByDay: Record<string, WeeklyPlanDetail["items"]> = {};
  for (const d of DAYS_OF_WEEK) itemsByDay[d] = [];
  for (const item of plan?.items ?? []) itemsByDay[item.day_of_week]?.push(item);
  for (const d of DAYS_OF_WEEK) itemsByDay[d].sort((a, b) => a.start_time.localeCompare(b.start_time));

  const issuesByDay = new Map<string, WeeklyPlanIssue[]>();
  const weekWideIssues: WeeklyPlanIssue[] = [];
  for (const issue of plan?.issues ?? []) {
    if (issue.day_of_week) {
      issuesByDay.set(issue.day_of_week, [...(issuesByDay.get(issue.day_of_week) ?? []), issue]);
    } else {
      weekWideIssues.push(issue);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <Link href={`/planner`} className="text-sm font-medium text-brand-700 hover:underline">
        ← Your workspaces
      </Link>

      <div className="mt-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Weekly planner</h1>
        <div className="flex items-center gap-2">
          <Button variant="secondary" className="text-sm" onClick={() => setWeekStart((d) => addDays(d, -7))}>
            ← Prev week
          </Button>
          <span className="text-sm font-medium text-slate-700">Week of {isoDate(weekStart)}</span>
          <Button variant="secondary" className="text-sm" onClick={() => setWeekStart((d) => addDays(d, 7))}>
            Next week →
          </Button>
        </div>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {dataLoading && <p className="mt-4 text-sm text-slate-500">Loading…</p>}

      {!dataLoading && !plan && !error && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 p-6 text-center">
          <p className="text-sm text-slate-500">Nothing planned for this week yet.</p>
          <Button className="mt-3 text-sm" onClick={handleStartPlanning}>
            Start planning this week
          </Button>
        </div>
      )}

      {plan && (
        <>
          {weekWideIssues.length > 0 && (
            <div className="mt-4 flex flex-col gap-2">
              {weekWideIssues.map((issue, i) => (
                <p key={i} className={`rounded-lg border px-3 py-2 text-xs ${SEVERITY_STYLE[issue.severity]}`}>
                  {issue.message}
                </p>
              ))}
            </div>
          )}

          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {DAYS_OF_WEEK.filter((d) => d !== "saturday" && d !== "sunday").map((d) => (
              <div key={d} className="rounded-xl border border-slate-200 p-4">
                <h2 className="text-sm font-semibold capitalize text-slate-900">{d}</h2>
                <div className="mt-2 flex flex-col gap-2">
                  {itemsByDay[d].length === 0 && <p className="text-xs text-slate-400">Nothing scheduled.</p>}
                  {itemsByDay[d].map((item) => (
                    <div key={item.id} className="rounded-lg border border-slate-100 bg-slate-50 p-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-900">{item.start_time.slice(0, 5)}</span>
                        <button onClick={() => handleDeleteItem(item.id)} className="text-red-600 hover:underline">
                          Remove
                        </button>
                      </div>
                      <p className="mt-0.5 text-slate-700">
                        {item.class_name} · {item.duration_minutes} min
                      </p>
                      {item.topic && <p className="text-slate-500">{item.topic}</p>}
                    </div>
                  ))}
                  {(issuesByDay.get(d) ?? []).map((issue, i) => (
                    <p key={i} className={`rounded-lg border px-2 py-1 text-xs ${SEVERITY_STYLE[issue.severity]}`}>
                      {issue.message}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <section className="mt-8 border-t border-slate-200 pt-6">
            <h2 className="text-lg font-semibold text-slate-900">Add a session</h2>
            <form onSubmit={handleAddItem} className="mt-4 grid gap-3 sm:grid-cols-2 sm:max-w-xl">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-slate-700">Day</label>
                <select
                  value={day}
                  onChange={(e) => setDay(e.target.value as DayOfWeek)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  {DAYS_OF_WEEK.map((d) => (
                    <option key={d} value={d} className="capitalize">
                      {d}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-slate-700">Class</label>
                <select
                  value={classId}
                  onChange={(e) => {
                    setClassId(e.target.value);
                    setLessonPlanId("");
                  }}
                  className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-slate-700">Lesson plan (optional)</label>
                <select
                  value={lessonPlanId}
                  onChange={(e) => setLessonPlanId(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  <option value="">None yet</option>
                  {(lessonPlansByClass[classId] ?? []).map((lp) => (
                    <option key={lp.id} value={lp.id}>
                      {lp.title}
                    </option>
                  ))}
                </select>
              </div>
              {!lessonPlanId && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-slate-700">Topic (placeholder)</label>
                  <input
                    value={topicOverride}
                    onChange={(e) => setTopicOverride(e.target.value)}
                    placeholder="e.g. Fractions"
                    className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                  />
                </div>
              )}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-slate-700">Start time</label>
                <input
                  type="time"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-slate-700">Duration (minutes)</label>
                <input
                  type="number"
                  min={1}
                  max={480}
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(Number(e.target.value))}
                  className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                />
              </div>
              {formError && <p className="sm:col-span-2 text-sm text-red-600">{formError}</p>}
              <Button type="submit" disabled={creating || !classId} className="self-start sm:col-span-2">
                {creating ? "Adding…" : "Add session"}
              </Button>
            </form>
          </section>
        </>
      )}
    </main>
  );
}
