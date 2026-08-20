"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { CourseDetail } from "@/types";

export default function CourseDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<CourseDetail>(`/courses/${slug}`)
      .then(setCourse)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? "Course not found." : "Couldn't load this course."))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  if (error || !course) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-red-600">{error ?? "Course not found."}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-3xl font-bold text-slate-900">{course.title}</h1>
      {course.description && <p className="mt-2 text-slate-600">{course.description}</p>}

      <div className="mt-10 flex flex-col gap-6">
        {course.chapters.map((chapter, i) => (
          <section key={chapter.id} className="rounded-xl border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900">
              {i + 1}. {chapter.title}
            </h2>
            <ul className="mt-3 flex flex-col gap-2">
              {chapter.topics.map((topic) => (
                <li key={topic.id}>
                  <p className="text-sm font-medium text-slate-800">{topic.title}</p>
                  <ul className="ml-4 mt-1 flex flex-col gap-1">
                    {topic.lessons.map((lesson) => (
                      <li key={lesson.id}>
                        <Link
                          href={`/lessons/${lesson.slug}`}
                          className="text-sm text-brand-700 hover:underline"
                        >
                          {lesson.title}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </section>
        ))}
        {course.chapters.length === 0 && (
          <p className="text-sm text-slate-500">No chapters have been published for this course yet.</p>
        )}
      </div>
    </main>
  );
}
