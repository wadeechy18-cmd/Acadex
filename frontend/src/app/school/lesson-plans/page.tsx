"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { LessonPlanSummary } from "@/types";

export default function SchoolLessonPlansPage() {
  const { school } = useAuth();
  const [plans, setPlans] = useState<LessonPlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topicFilter, setTopicFilter] = useState("");

  function loadPlans() {
    if (!school) return;
    setLoading(true);
    const params = new URLSearchParams();
    if (topicFilter) params.set("topic", topicFilter);
    const query = params.toString();
    apiFetch<LessonPlanSummary[]>(`/schools/${school.id}/lesson-plans${query ? `?${query}` : ""}`, undefined, true)
      .then(setPlans)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load lesson plans."))
      .finally(() => setLoading(false));
  }

  useEffect(loadPlans, [school, topicFilter]);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Lesson Plans</h1>
      <p className="mt-1 text-sm text-muted-foreground">Lesson plans created by teachers in your school.</p>

      <div className="mt-6 max-w-xs">
        <Label className="text-xs">Search by topic</Label>
        <Input value={topicFilter} onChange={(e) => setTopicFilter(e.target.value)} placeholder="e.g. fractions" />
      </div>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && plans.length === 0 && <p className="mt-8 text-sm text-muted-foreground">No lesson plans found.</p>}

      {!loading && !error && plans.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {plans.map((p) => (
            <Link
              key={p.id}
              href={`/school/lesson-plans/${p.id}`}
              className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent"
            >
              <div>
                <p className="font-medium">{p.topic_title}</p>
                <p className="text-sm text-muted-foreground">
                  {p.owner_display_name} · {p.subject_name} · {p.year_group_name} · {p.duration_minutes} min
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
