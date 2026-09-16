"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { LessonPlan, LessonPlanSummary, SubjectSummary, YearGroupSummary } from "@/types";

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export default function LessonPlanCurriculumLibraryPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<LessonPlanSummary[]>([]);
  const [yearGroups, setYearGroups] = useState<YearGroupSummary[]>([]);
  const [subjects, setSubjects] = useState<SubjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [duplicatingId, setDuplicatingId] = useState<string | null>(null);

  const [topicFilter, setTopicFilter] = useState("");
  const [yearGroupFilter, setYearGroupFilter] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");

  function loadPlans() {
    setLoading(true);
    const params = new URLSearchParams();
    if (topicFilter) params.set("topic", topicFilter);
    if (yearGroupFilter) params.set("year_group_id", yearGroupFilter);
    if (subjectFilter) params.set("subject_id", subjectFilter);
    const query = params.toString();
    apiFetch<LessonPlanSummary[]>(`/lesson-plans/library${query ? `?${query}` : ""}`, undefined, true)
      .then(setPlans)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load the curriculum library."))
      .finally(() => setLoading(false));
  }

  useEffect(loadPlans, [topicFilter, yearGroupFilter, subjectFilter]);

  useEffect(() => {
    apiFetch<{ id: string; name: string }[]>("/curriculum/curricula", undefined, true).then((curricula) => {
      const curriculum = curricula[0];
      if (!curriculum) return;
      apiFetch<SubjectSummary[]>(`/curriculum/curricula/${curriculum.id}/subjects`, undefined, true).then(setSubjects);
      apiFetch<{ id: string; code: string; name: string; sort_order: number }[]>(`/curriculum/curricula/${curriculum.id}/key-stages`, undefined, true).then(
        async (keyStages) => {
          const lists = await Promise.all(
            keyStages.map((ks) => apiFetch<YearGroupSummary[]>(`/curriculum/key-stages/${ks.id}/year-groups`, undefined, true))
          );
          setYearGroups(lists.flat());
        }
      );
    });
  }, []);

  async function handleUse(planId: string) {
    setDuplicatingId(planId);
    try {
      const copy = await apiFetch<LessonPlan>(`/lesson-plans/library/${planId}/duplicate`, { method: "POST" }, true);
      router.push(`/teacher/lesson-plans/${copy.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't copy this lesson plan.");
      setDuplicatingId(null);
    }
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Curriculum Library</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Ready-made EYFS and Key Stage 1 lesson plans from the England National Curriculum -- browse and use one as your
        starting point, no AI generation needed. Using one copies it into your own lesson plans, so you can edit it
        freely without changing the shared original.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <Label className="text-xs">Topic</Label>
          <Input placeholder="Search topic" value={topicFilter} onChange={(e) => setTopicFilter(e.target.value)} />
        </div>
        <div>
          <Label className="text-xs">Year group</Label>
          <select className={selectClass} value={yearGroupFilter} onChange={(e) => setYearGroupFilter(e.target.value)}>
            <option value="">All year groups</option>
            {yearGroups.map((y) => (
              <option key={y.id} value={y.id}>
                {y.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label className="text-xs">Subject</Label>
          <select className={selectClass} value={subjectFilter} onChange={(e) => setSubjectFilter(e.target.value)}>
            <option value="">All subjects</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}
      {!loading && !error && plans.length === 0 && (
        <p className="mt-8 text-sm text-muted-foreground">
          No library plans match those filters.{" "}
          <Link href="/teacher/lesson-planner" className="underline">
            Generate your own instead.
          </Link>
        </p>
      )}

      {!loading && !error && plans.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {plans.map((p) => (
            <div key={p.id} className="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium">{p.topic_title}</p>
                <p className="text-sm text-muted-foreground">
                  {p.subject_name} · {p.year_group_name} · {p.duration_minutes} min
                </p>
              </div>
              <Button size="sm" disabled={duplicatingId === p.id} onClick={() => handleUse(p.id)}>
                {duplicatingId === p.id ? "Copying…" : "Use this plan"}
              </Button>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
