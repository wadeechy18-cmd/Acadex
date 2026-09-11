"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { LessonPlan, LessonPlanTemplateType } from "@/types";

const TEMPLATE_OPTIONS: { value: LessonPlanTemplateType; label: string }[] = [
  { value: "standard", label: "Standard Lesson" },
  { value: "practical", label: "Practical Lesson" },
  { value: "revision", label: "Revision Lesson" },
  { value: "exam_prep", label: "Exam Preparation" },
  { value: "new_topic", label: "New Topic" },
  { value: "retrieval", label: "Retrieval Lesson" },
  { value: "assessment", label: "Assessment Lesson" },
  { value: "review", label: "Review Lesson" },
  { value: "double", label: "Double Lesson" },
  { value: "short", label: "Short Lesson" },
];

export default function LessonPlansPage() {
  const { orgId, classId } = useParams<{ orgId: string; classId: string }>();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [plans, setPlans] = useState<LessonPlan[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [topic, setTopic] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(50);
  const [templateType, setTemplateType] = useState<LessonPlanTemplateType>("standard");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "teacher")) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  function loadPlans() {
    setDataLoading(true);
    apiFetch<LessonPlan[]>(`/classes/${classId}/lesson-plans`, undefined, true)
      .then(setPlans)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load lesson plans."))
      .finally(() => setDataLoading(false));
  }

  useEffect(() => {
    if (!user || user.role !== "teacher" || !classId) return;
    loadPlans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, classId]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setCreating(true);
    try {
      const plan = await apiFetch<LessonPlan>(
        `/classes/${classId}/lesson-plans`,
        {
          method: "POST",
          body: JSON.stringify({ title, topic, duration_minutes: durationMinutes, template_type: templateType }),
        },
        true
      );
      router.push(`/planner/${orgId}/classes/${classId}/lesson-plans/${plan.id}`);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Couldn't create the lesson plan.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDuplicate(planId: string) {
    await apiFetch(`/lesson-plans/${planId}/duplicate`, { method: "POST" }, true);
    loadPlans();
  }

  async function handleDelete(planId: string) {
    await apiFetch(`/lesson-plans/${planId}`, { method: "DELETE" }, true);
    loadPlans();
  }

  if (loading || !user) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href={`/planner/${orgId}/classes`} className="text-sm font-medium text-brand-700 hover:underline">
        ← Classes
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-slate-900">Lesson plans</h1>

      {dataLoading && <p className="mt-8 text-sm text-slate-500">Loading…</p>}
      {error && <p className="mt-8 text-sm text-red-600">{error}</p>}

      {!dataLoading && !error && (
        <div className="mt-8 flex flex-col gap-3">
          {plans.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-5">
              <Link href={`/planner/${orgId}/classes/${classId}/lesson-plans/${p.id}`} className="flex-1">
                <h2 className="font-semibold text-slate-900 hover:text-brand-700">{p.title}</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {p.topic} · {p.duration_minutes} min · v{p.latest_version_number} ·{" "}
                  <span className={p.status === "published" ? "text-green-700" : "text-amber-700"}>{p.status}</span>
                </p>
              </Link>
              {p.teacher_user_id === user.id && (
                <div className="flex gap-2">
                  <Button variant="secondary" className="text-sm" onClick={() => handleDuplicate(p.id)}>
                    Duplicate
                  </Button>
                  <Button variant="secondary" className="text-sm" onClick={() => handleDelete(p.id)}>
                    Delete
                  </Button>
                </div>
              )}
            </div>
          ))}
          {plans.length === 0 && (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
              No lesson plans yet — create your first one below.
            </p>
          )}
        </div>
      )}

      <section className="mt-10 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-slate-900">Create a lesson plan</h2>
        <form onSubmit={handleCreate} className="mt-4 flex flex-col gap-4 sm:max-w-md">
          <Input label="Title" name="title" required value={title} onChange={(e) => setTitle(e.target.value)} />
          <Input label="Topic" name="topic" required value={topic} onChange={(e) => setTopic(e.target.value)} />
          <Input
            label="Duration (minutes)"
            name="durationMinutes"
            type="number"
            min={1}
            max={300}
            required
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(Number(e.target.value))}
          />
          <div className="flex flex-col gap-1.5">
            <label htmlFor="templateType" className="text-sm font-medium text-slate-700">
              Lesson type
            </label>
            <select
              id="templateType"
              value={templateType}
              onChange={(e) => setTemplateType(e.target.value as LessonPlanTemplateType)}
              className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              {TEMPLATE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          {formError && (
            <p role="alert" className="text-sm text-red-600">
              {formError}
            </p>
          )}
          <Button type="submit" disabled={creating} className="self-start">
            {creating ? "Creating…" : "Create lesson plan"}
          </Button>
        </form>
      </section>
    </main>
  );
}
