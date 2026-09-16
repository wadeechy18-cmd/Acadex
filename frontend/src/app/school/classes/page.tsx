"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { ClassSummary } from "@/types";

export default function SchoolClassesPage() {
  const { school } = useAuth();
  const [classes, setClasses] = useState<ClassSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!school) return;
    apiFetch<ClassSummary[]>(`/schools/${school.id}/classes`, undefined, true)
      .then(setClasses)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load classes."))
      .finally(() => setLoading(false));
  }, [school]);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Classes</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Classes across your school's teachers -- each teacher creates their own classes from their Classes page; used
        for lesson plan assignment and the timetable.
      </p>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}
      {!loading && !error && classes.length === 0 && (
        <p className="mt-8 text-sm text-muted-foreground">No classes yet -- teachers can add these from their own Classes page.</p>
      )}

      {!loading && !error && classes.length > 0 && (
        <div className="mt-6 flex flex-col gap-2">
          {classes.map((c) => (
            <div key={c.id} className="rounded-md border p-3 text-sm">
              <p className="font-medium">{c.name}</p>
              <p className="text-muted-foreground">
                {c.subject_name ?? "No subject"} · {c.year_group_name ?? "No year group"}
              </p>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
