"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { NoteBlocks } from "@/components/notes/NoteBlocks";
import { VideoPlayer } from "@/components/lesson/VideoPlayer";
import { TopicDiscussions } from "@/components/community/TopicDiscussions";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { LessonDetail } from "@/types";

export default function LessonPage() {
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuth();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completion, setCompletion] = useState(0);
  const savingRef = useRef(false);

  useEffect(() => {
    apiFetch<LessonDetail>(`/lessons/${slug}`, undefined, true)
      .then((data) => {
        setLesson(data);
        setCompletion(data.my_progress?.completion_percentage ?? 0);
      })
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? "Lesson not found." : "Couldn't load this lesson."))
      .finally(() => setLoading(false));
  }, [slug]);

  const saveProgress = useCallback(
    async (percentage: number, positionSeconds?: number) => {
      if (!lesson || !user || user.role !== "student" || savingRef.current) return;
      savingRef.current = true;
      try {
        await apiFetch(
          `/progress/${lesson.topic_id}`,
          {
            method: "PUT",
            body: JSON.stringify({
              completion_percentage: percentage,
              ...(positionSeconds !== undefined ? { last_position_seconds: Math.round(positionSeconds) } : {}),
            }),
          },
          true
        );
        setCompletion(percentage);
      } finally {
        savingRef.current = false;
      }
    },
    [lesson, user]
  );

  if (loading) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  if (error || !lesson) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-red-600">{error ?? "Lesson not found."}</p>
      </main>
    );
  }

  const { breadcrumb } = lesson;
  const isComplete = completion >= 100;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <nav className="flex flex-wrap items-center gap-1 text-sm text-slate-500">
        <Link href={`/subjects/${breadcrumb.subject.slug}`} className="hover:underline">
          {breadcrumb.subject.name}
        </Link>
        <span>/</span>
        <Link href={`/courses/${breadcrumb.course.slug}`} className="hover:underline">
          {breadcrumb.course.title}
        </Link>
        <span>/</span>
        <span>{breadcrumb.chapter.title}</span>
        <span>/</span>
        <span>{breadcrumb.topic.title}</span>
      </nav>

      <div className="mt-4 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-slate-900">{lesson.title}</h1>
        {user?.role === "student" && (
          <Button
            variant={isComplete ? "secondary" : "primary"}
            onClick={() => saveProgress(isComplete ? 0 : 100)}
          >
            {isComplete ? "Mark incomplete" : "Mark complete"}
          </Button>
        )}
      </div>

      {lesson.video && (
        <div className="mt-6">
          <VideoPlayer
            video={lesson.video}
            resumeSeconds={lesson.my_progress?.last_position_seconds}
            onProgress={(position, duration) => {
              if (!duration) return;
              const pct = Math.min(100, Math.round((position / duration) * 100));
              if (pct > completion) saveProgress(pct, position);
            }}
            onEnded={() => saveProgress(100)}
          />
        </div>
      )}

      {lesson.notes.length > 0 && (
        <div className="mt-8 flex flex-col gap-8">
          {lesson.notes.map((note) => (
            <section key={note.id}>
              <NoteBlocks blocks={note.content_blocks} />
            </section>
          ))}
        </div>
      )}

      {!lesson.video && lesson.notes.length === 0 && (
        <p className="mt-8 text-sm text-slate-500">Content for this lesson is coming soon.</p>
      )}

      <div className="mt-10 border-t border-slate-200 pt-6">
        <Link
          href={`/practice?topic_id=${breadcrumb.topic.id}&subject_id=${breadcrumb.subject.id}`}
          className="text-sm font-medium text-brand-700 hover:underline"
        >
          Practice questions on this topic →
        </Link>
      </div>

      <div className="mt-8 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-slate-900">Discussion</h2>
        <div className="mt-4">
          <TopicDiscussions topicId={breadcrumb.topic.id} />
        </div>
      </div>
    </main>
  );
}
