"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { LessonPlanSummary } from "@/types";

export default function LessonPlansLibraryPage() {
  const [plans, setPlans] = useState<LessonPlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadPlans() {
    setLoading(true);
    apiFetch<LessonPlanSummary[]>("/lesson-plans", undefined, true)
      .then(setPlans)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load lesson plans."))
      .finally(() => setLoading(false));
  }

  useEffect(loadPlans, []);

  async function handleDuplicate(id: string) {
    await apiFetch(`/lesson-plans/${id}/duplicate`, { method: "POST" }, true);
    loadPlans();
  }

  async function handleDelete(id: string) {
    await apiFetch(`/lesson-plans/${id}`, { method: "DELETE" }, true);
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

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && plans.length === 0 && (
        <p className="mt-8 text-sm text-muted-foreground">
          No lesson plans yet. <Link href="/teacher/lesson-planner" className="underline">Create your first one.</Link>
        </p>
      )}

      {!loading && !error && plans.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {plans.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded-lg border p-4">
              <div>
                <Link href={`/teacher/lesson-plans/${p.id}`} className="font-medium hover:underline">
                  {p.topic_title}
                </Link>
                <p className="text-sm text-muted-foreground">
                  {p.subject_name} · {p.year_group_name} · {p.duration_minutes} min · v{p.current_version_number}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
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
