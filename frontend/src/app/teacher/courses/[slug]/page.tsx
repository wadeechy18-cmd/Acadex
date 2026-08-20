"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api-client";
import type { Chapter, CourseDetail, StudentProgressRow, Topic } from "@/types";

function slugify(text: string): string {
  return `${text.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString(36)}`;
}

export default function TeacherCoursePage() {
  const { slug } = useParams<{ slug: string }>();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [students, setStudents] = useState<StudentProgressRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [newChapterTitle, setNewChapterTitle] = useState("");
  const [newTopicTitle, setNewTopicTitle] = useState<Record<string, string>>({});
  const [newLessonTitle, setNewLessonTitle] = useState<Record<string, string>>({});

  async function refresh() {
    const data = await apiFetch<CourseDetail>(`/courses/${slug}`, undefined, true);
    setCourse(data);
    setLoading(false);
  }

  useEffect(() => {
    apiFetch<CourseDetail>(`/courses/${slug}`, undefined, true)
      .then(setCourse)
      .finally(() => setLoading(false));
  }, [slug]);

  async function togglePublish() {
    if (!course) return;
    await apiFetch(`/courses/${course.id}`, { method: "PATCH", body: JSON.stringify({ is_published: !course.is_published }) }, true);
    refresh();
  }

  async function toggleLessonPublish(lessonId: string, current: boolean) {
    await apiFetch(`/lessons/${lessonId}`, { method: "PATCH", body: JSON.stringify({ is_published: !current }) }, true);
    refresh();
  }

  async function createChapter() {
    if (!course || !newChapterTitle.trim()) return;
    await apiFetch(
      "/chapters",
      { method: "POST", body: JSON.stringify({ course_id: course.id, title: newChapterTitle, slug: slugify(newChapterTitle) }) },
      true
    );
    setNewChapterTitle("");
    refresh();
  }

  async function createTopic(chapter: Chapter) {
    const title = newTopicTitle[chapter.id];
    if (!title?.trim()) return;
    await apiFetch("/topics", { method: "POST", body: JSON.stringify({ chapter_id: chapter.id, title, slug: slugify(title) }) }, true);
    setNewTopicTitle((prev) => ({ ...prev, [chapter.id]: "" }));
    refresh();
  }

  async function createLesson(topic: Topic) {
    const title = newLessonTitle[topic.id];
    if (!title?.trim()) return;
    await apiFetch(
      "/lessons",
      { method: "POST", body: JSON.stringify({ topic_id: topic.id, title, slug: slugify(title), lesson_type: "mixed" }) },
      true
    );
    setNewLessonTitle((prev) => ({ ...prev, [topic.id]: "" }));
    refresh();
  }

  async function loadStudents() {
    if (!course) return;
    setStudents(await apiFetch<StudentProgressRow[]>(`/courses/${course.id}/students`, undefined, true));
  }

  if (loading || !course) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-slate-900">{course.title}</h1>
        <Button variant={course.is_published ? "secondary" : "primary"} onClick={togglePublish}>
          {course.is_published ? "Unpublish course" : "Publish course"}
        </Button>
      </div>

      <div className="mt-8 flex flex-col gap-6">
        {course.chapters.map((chapter, ci) => (
          <section key={chapter.id} className="rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900">
              {ci + 1}. {chapter.title}
            </h2>

            <div className="mt-3 flex flex-col gap-3">
              {chapter.topics.map((topic) => (
                <div key={topic.id} className="rounded-lg bg-slate-50 p-3">
                  <p className="text-sm font-medium text-slate-800">{topic.title}</p>
                  <ul className="mt-2 flex flex-col gap-1">
                    {topic.lessons.map((lesson) => (
                      <li key={lesson.id} className="flex items-center justify-between text-sm">
                        <span>{lesson.title}</span>
                        <button
                          onClick={() => toggleLessonPublish(lesson.id, lesson.is_published)}
                          className={lesson.is_published ? "text-green-700" : "text-amber-700"}
                        >
                          {lesson.is_published ? "Published" : "Draft"}
                        </button>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-2 flex gap-2">
                    <input
                      value={newLessonTitle[topic.id] ?? ""}
                      onChange={(e) => setNewLessonTitle((prev) => ({ ...prev, [topic.id]: e.target.value }))}
                      placeholder="New lesson title…"
                      className="flex-1 rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs"
                    />
                    <button
                      onClick={() => createLesson(topic)}
                      className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
                    >
                      Add lesson
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 flex gap-2">
              <input
                value={newTopicTitle[chapter.id] ?? ""}
                onChange={(e) => setNewTopicTitle((prev) => ({ ...prev, [chapter.id]: e.target.value }))}
                placeholder="New topic title…"
                className="flex-1 rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
              />
              <button
                onClick={() => createTopic(chapter)}
                className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-900"
              >
                Add topic
              </button>
            </div>
          </section>
        ))}
      </div>

      <div className="mt-6 flex gap-2">
        <input
          value={newChapterTitle}
          onChange={(e) => setNewChapterTitle(e.target.value)}
          placeholder="New chapter title…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button onClick={createChapter} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
          Add chapter
        </button>
      </div>

      <section className="mt-10 border-t border-slate-200 pt-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Students</h2>
          {!students && (
            <Button variant="secondary" onClick={loadStudents}>
              Load students
            </Button>
          )}
        </div>
        {students && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="pb-2">Student</th>
                  <th className="pb-2">Progress</th>
                  <th className="pb-2">Enrolled</th>
                </tr>
              </thead>
              <tbody>
                {students.map((row) => (
                  <tr key={row.student.id} className="border-b border-slate-100">
                    <td className="py-2">{row.student.display_name}</td>
                    <td className="py-2">{row.completion_percentage}%</td>
                    <td className="py-2">{new Date(row.enrolled_at).toLocaleDateString()}</td>
                  </tr>
                ))}
                {students.length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-4 text-center text-slate-500">
                      No students enrolled yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
