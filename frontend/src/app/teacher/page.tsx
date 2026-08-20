"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Course, Subject } from "@/types";

export default function TeacherDashboardPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [coursesBySubject, setCoursesBySubject] = useState<Record<string, Course[]>>({});
  const [dataLoading, setDataLoading] = useState(true);
  const [newCourseTitle, setNewCourseTitle] = useState("");
  const [newCourseSubjectId, setNewCourseSubjectId] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!loading && (!user || (user.role !== "teacher" && user.role !== "admin"))) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  async function loadSubjects() {
    const subjectList = await apiFetch<Subject[]>("/teachers/me/subjects", undefined, true);
    setSubjects(subjectList);
    const entries = await Promise.all(
      subjectList.map(async (s) => {
        const detail = await apiFetch<{ courses: Course[] }>(`/subjects/${s.slug}`, undefined, true);
        return [s.id, detail.courses] as const;
      })
    );
    setCoursesBySubject(Object.fromEntries(entries));
    setDataLoading(false);
  }

  useEffect(() => {
    async function init() {
      if (user && (user.role === "teacher" || user.role === "admin")) {
        await loadSubjects();
      }
    }
    init();
  }, [user]);

  async function handleCreateCourse(e: React.FormEvent) {
    e.preventDefault();
    if (!newCourseSubjectId || !newCourseTitle.trim()) return;
    setCreating(true);
    try {
      const slug = `${newCourseTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString(36)}`;
      await apiFetch(
        "/courses",
        { method: "POST", body: JSON.stringify({ subject_id: newCourseSubjectId, title: newCourseTitle, slug }) },
        true
      );
      setNewCourseTitle("");
      loadSubjects();
    } finally {
      setCreating(false);
    }
  }

  if (loading || !user) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Teacher dashboard</h1>
      <p className="mt-1 text-sm text-slate-600">Manage courses in your assigned subjects.</p>

      {dataLoading ? (
        <p className="mt-8 text-sm text-slate-500">Loading…</p>
      ) : subjects.length === 0 ? (
        <p className="mt-8 rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
          You haven&apos;t been assigned to any subjects yet. An admin needs to assign you before you can create
          content.
        </p>
      ) : (
        <div className="mt-8 flex flex-col gap-8">
          {subjects.map((subject) => (
            <section key={subject.id}>
              <h2 className="text-lg font-semibold text-slate-900">{subject.name}</h2>
              <div className="mt-3 flex flex-col gap-2">
                {(coursesBySubject[subject.id] ?? []).map((course) => (
                  <Link
                    key={course.id}
                    href={`/teacher/courses/${course.slug}`}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 text-sm hover:border-brand-300 hover:bg-brand-50"
                  >
                    <span className="font-medium text-slate-900">{course.title}</span>
                    <span className={course.is_published ? "text-green-700" : "text-amber-700"}>
                      {course.is_published ? "Published" : "Draft"}
                    </span>
                  </Link>
                ))}
                {(coursesBySubject[subject.id] ?? []).length === 0 && (
                  <p className="text-sm text-slate-500">No courses yet in this subject.</p>
                )}
              </div>
            </section>
          ))}
        </div>
      )}

      <section className="mt-10 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-slate-900">Create a new course</h2>
        <form onSubmit={handleCreateCourse} className="mt-4 flex flex-col gap-4 sm:max-w-md">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="subject" className="text-sm font-medium text-slate-700">
              Subject
            </label>
            <select
              id="subject"
              value={newCourseSubjectId}
              onChange={(e) => setNewCourseSubjectId(e.target.value)}
              className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <option value="">Select a subject</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <Input label="Course title" value={newCourseTitle} onChange={(e) => setNewCourseTitle(e.target.value)} />
          <Button type="submit" disabled={creating} className="self-start">
            {creating ? "Creating…" : "Create course"}
          </Button>
        </form>
      </section>
    </main>
  );
}
