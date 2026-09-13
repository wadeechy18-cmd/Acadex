"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { ClassSummary, LessonPlanSummary } from "@/types";

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export default function LessonPlansLibraryPage() {
  const [plans, setPlans] = useState<LessonPlanSummary[]>([]);
  const [classes, setClasses] = useState<ClassSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [topicFilter, setTopicFilter] = useState("");
  const [classFilter, setClassFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  function loadPlans() {
    setLoading(true);
    const params = new URLSearchParams();
    if (topicFilter) params.set("topic", topicFilter);
    if (classFilter) params.set("class_id", classFilter);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const query = params.toString();
    apiFetch<LessonPlanSummary[]>(`/lesson-plans${query ? `?${query}` : ""}`, undefined, true)
      .then(setPlans)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load lesson plans."))
      .finally(() => setLoading(false));
  }

  useEffect(loadPlans, [topicFilter, classFilter, dateFrom, dateTo]);
  useEffect(() => {
    apiFetch<ClassSummary[]>("/classes", undefined, true).then(setClasses);
  }, []);

  async function handleDuplicate(id: string) {
    await apiFetch(`/lesson-plans/${id}/duplicate`, { method: "POST" }, true);
    loadPlans();
  }

  async function handleDelete(id: string) {
    await apiFetch(`/lesson-plans/${id}`, { method: "DELETE" }, true);
    loadPlans();
  }

  async function handleAssign(id: string, classId: string) {
    await apiFetch(`/lesson-plans/${id}/assign`, { method: "PATCH", body: JSON.stringify({ class_id: classId || null }) }, true);
    loadPlans();
  }

  return (
    <main className="p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Lesson Plans</h1>
        <Link href="/teacher/lesson-planner">
          <Button>New lesson plan</Button>
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <Label className="text-xs">Topic</Label>
          <Input placeholder="Search topic" value={topicFilter} onChange={(e) => setTopicFilter(e.target.value)} />
        </div>
        <div>
          <Label className="text-xs">Class</Label>
          <select className={selectClass} value={classFilter} onChange={(e) => setClassFilter(e.target.value)}>
            <option value="">All classes</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label className="text-xs">Updated from</Label>
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div>
          <Label className="text-xs">Updated to</Label>
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
      </div>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && plans.length === 0 && (
        <p className="mt-8 text-sm text-muted-foreground">
          No lesson plans match. <Link href="/teacher/lesson-planner" className="underline">Create one.</Link>
        </p>
      )}

      {!loading && !error && plans.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {plans.map((p) => (
            <div key={p.id} className="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <Link href={`/teacher/lesson-plans/${p.id}`} className="font-medium hover:underline">
                  {p.topic_title}
                </Link>
                <p className="text-sm text-muted-foreground">
                  {p.subject_name} · {p.year_group_name} · {p.duration_minutes} min · v{p.current_version_number}
                  {p.class_name && ` · ${p.class_name}`}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className={`${selectClass} w-40`}
                  value={p.class_id ?? ""}
                  onChange={(e) => handleAssign(p.id, e.target.value)}
                >
                  <option value="">Unassigned</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <Link href={`/teacher/lesson-plans/${p.id}`}>
                  <Button variant="outline" size="sm">
                    Open
                  </Button>
                </Link>
                <Button variant="outline" size="sm" onClick={() => handleDuplicate(p.id)}>
                  Duplicate
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDelete(p.id)}>
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
