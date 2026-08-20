"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { SubjectDetail } from "@/types";

export default function SubjectDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [subject, setSubject] = useState<SubjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<SubjectDetail>(`/subjects/${slug}`)
      .then(setSubject)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? "Subject not found." : "Couldn't load this subject."))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  if (error || !subject) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-red-600">{error ?? "Subject not found."}</p>
        <Link href="/subjects" className="mt-4 inline-block text-sm text-brand-700 hover:underline">
          ← Back to subjects
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <Link href="/subjects" className="text-sm font-medium text-brand-700 hover:underline">
        ← Back to subjects
      </Link>
      <h1 className="mt-4 text-3xl font-bold text-slate-900">{subject.name}</h1>
      {subject.description && <p className="mt-2 text-slate-600">{subject.description}</p>}

      <h2 className="mt-10 text-xl font-semibold text-slate-900">Courses</h2>
      {subject.courses.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No courses have been published for this subject yet.</p>
      ) : (
        <div className="mt-4 flex flex-col gap-3">
          {subject.courses.map((course) => (
            <Link
              key={course.id}
              href={`/courses/${course.slug}`}
              className="rounded-xl border border-slate-200 p-5 transition-colors hover:border-brand-300 hover:bg-brand-50"
            >
              <h3 className="font-semibold text-slate-900">{course.title}</h3>
              {course.description && <p className="mt-1 text-sm text-slate-600">{course.description}</p>}
              {!course.is_published && (
                <span className="mt-2 inline-block rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                  Draft
                </span>
              )}
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
