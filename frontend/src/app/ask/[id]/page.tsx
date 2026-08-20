"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CommentThread } from "@/components/community/CommentThread";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { QuestionThreadDetail } from "@/types";

export default function QuestionThreadPage() {
  const { id } = useParams<{ id: string }>();
  const [thread, setThread] = useState<QuestionThreadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<QuestionThreadDetail>(`/question-threads/${id}`, undefined, true)
      .then(setThread)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? "Question not found." : "Couldn't load this question."))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  if (error || !thread) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-red-600">{error ?? "Question not found."}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <span className="inline-block rounded-full bg-slate-100 px-3 py-1 text-xs font-medium capitalize text-slate-600">
        {thread.status}
      </span>
      {thread.description && <p className="mt-4 text-lg text-slate-900">{thread.description}</p>}

      {thread.images.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-3">
          {thread.images.map((img) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img key={img.id} src={img.url} alt="Uploaded question" className="max-h-96 rounded-lg border border-slate-200" />
          ))}
        </div>
      )}

      <div className="mt-8 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-slate-900">Discussion</h2>
        <div className="mt-4">
          <CommentThread
            contextId={thread.id}
            contextField="question_thread_id"
            fetchUrl={`/question-threads/${thread.id}/comments`}
          />
        </div>
      </div>
    </main>
  );
}
