"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { LessonPlan } from "@/types";

const SECTIONS: { key: keyof LessonPlan["current_version"]["content"]; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "prior_knowledge", label: "Prior knowledge" },
  { key: "starter", label: "Starter" },
  { key: "teacher_explanation", label: "Teacher explanation" },
  { key: "guided_practice", label: "Guided practice" },
  { key: "independent_practice", label: "Independent practice" },
  { key: "assessment", label: "Assessment" },
  { key: "plenary", label: "Plenary" },
  { key: "homework", label: "Homework" },
];

const LIST_SECTIONS: { key: keyof LessonPlan["current_version"]["content"]; label: string }[] = [
  { key: "learning_objectives", label: "Learning objectives" },
  { key: "success_criteria", label: "Success criteria" },
  { key: "key_vocabulary", label: "Key vocabulary" },
];

export default function SchoolLessonPlanViewPage() {
  const params = useParams();
  const planId = params.id as string;
  const { school } = useAuth();

  const [plan, setPlan] = useState<LessonPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!school) return;
    apiFetch<LessonPlan>(`/schools/${school.id}/lesson-plans/${planId}`, undefined, true)
      .then(setPlan)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load this lesson plan."))
      .finally(() => setLoading(false));
  }, [school, planId]);

  if (loading) return <main className="p-8 text-sm text-muted-foreground">Loading…</main>;
  if (error) return <main className="p-8 text-sm text-destructive">{error}</main>;
  if (!plan) return null;

  const content = plan.current_version.content;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-bold">{content.title}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {plan.subject_name} · {plan.year_group_name} · {plan.duration_minutes} min · {plan.ability_level}
      </p>

      {plan.current_version.safeguarding_flagged && (
        <div className="mt-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {plan.current_version.safeguarding_notes}
        </div>
      )}

      <div className="mt-8 flex flex-col gap-6">
        {SECTIONS.map(({ key, label }) => (
          <section key={key}>
            <h2 className="font-semibold">{label}</h2>
            <p className="mt-1 text-sm">{content[key] as string}</p>
          </section>
        ))}
        {LIST_SECTIONS.map(({ key, label }) => (
          <section key={key}>
            <h2 className="font-semibold">{label}</h2>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {(content[key] as string[]).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </section>
        ))}
        <section>
          <h2 className="font-semibold">Timeline</h2>
          <div className="mt-2 flex flex-col gap-2">
            {content.timeline.map((entry, i) => (
              <div key={i} className="rounded-md border p-3 text-sm">
                <p className="font-medium">
                  {entry.start_minute}-{entry.end_minute} min: {entry.activity}
                </p>
                <p className="text-muted-foreground">{entry.description}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
