"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CourseDetail, EnrollmentWithCourse } from "@/types";

export default function CourseDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [enrolled, setEnrolled] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    apiFetch<CourseDetail>(`/courses/${slug}`)
      .then(setCourse)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? "Course not found." : "Couldn't load this course."))
      .finally(() => setLoading(false));
  }, [slug]);

  useEffect(() => {
    if (!user || user.role !== "student" || !course) return;
    apiFetch<EnrollmentWithCourse[]>("/enrollments/me", undefined, true)
      .then((enrollments) => setEnrolled(enrollments.some((e) => e.course_id === course.id)))
      .catch(() => {});
  }, [user, course]);

  async function handleEnroll() {
    if (!user) {
      router.push("/login");
      return;
    }
    if (!course) return;
    setEnrolling(true);
    try {
      await apiFetch("/enrollments", { method: "POST", body: JSON.stringify({ course_id: course.id }) }, true);
      setEnrolled(true);
    } finally {
      setEnrolling(false);
    }
  }

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
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">{course.title}</h1>
          {course.description && <p className="mt-2 text-slate-600">{course.description}</p>}
        </div>
        {(!user || user.role === "student") &&
          (enrolled ? (
            <span className="shrink-0 rounded-full bg-green-100 px-4 py-2 text-sm font-medium text-green-800">
              Enrolled
            </span>
          ) : (
            <Button onClick={handleEnroll} disabled={enrolling} className="shrink-0">
              {enrolling ? "Enrolling…" : "Enroll"}
            </Button>
          ))}
      </div>

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
                        <Link href={`/lessons/${lesson.slug}`} className="text-sm text-brand-700 hover:underline">
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
