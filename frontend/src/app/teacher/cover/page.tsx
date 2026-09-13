"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { TimetableExceptionCover } from "@/types";

export default function TeacherCoverPage() {
  const [covers, setCovers] = useState<TimetableExceptionCover[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<TimetableExceptionCover[]>("/timetable-exceptions/mine", undefined, true)
      .then(setCovers)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load your cover assignments."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Cover</h1>
      <p className="mt-1 text-sm text-muted-foreground">Lessons you've been asked to cover for an absent colleague.</p>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && covers.length === 0 && <p className="mt-8 text-sm text-muted-foreground">No cover assignments yet.</p>}

      {!loading && !error && covers.length > 0 && (
        <div className="mt-8 flex flex-col gap-3">
          {covers.map((c) => (
            <div key={c.id} className="rounded-lg border p-4">
              <p className="font-medium">
                {c.date} · {c.time_slot_label} · {c.subject_name}
              </p>
              <p className="text-sm text-muted-foreground">
                Covering for {c.original_teacher_name}
                {c.class_name && ` · ${c.class_name}`}
                {c.room_name && ` · ${c.room_name}`}
              </p>
              <div className="mt-3 rounded-md bg-muted/40 p-3">
                {c.cover_lesson_plan_id ? (
                  <>
                    <p className="text-sm font-medium">{c.cover_lesson_plan_title}</p>
                    <p className="text-xs text-muted-foreground">{c.cover_lesson_plan_message}</p>
                    <Link href={`/teacher/lesson-plans/${c.cover_lesson_plan_id}`} className="mt-2 inline-block text-sm underline">
                      Open lesson plan
                    </Link>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">{c.cover_lesson_plan_message}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
