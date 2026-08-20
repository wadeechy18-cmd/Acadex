"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { QuestionThread, Subject } from "@/types";

export default function AskQuestionPage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-xl px-6 py-12">
          <p className="text-sm text-slate-500">Loading…</p>
        </main>
      }
    >
      <AskQuestionPageInner />
    </Suspense>
  );
}

function AskQuestionPageInner() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const params = useSearchParams();

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectId, setSubjectId] = useState(params.get("subject_id") ?? "");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Subject[]>("/subjects").then(setSubjects);
  }, []);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!subjectId) {
      setError("Please select a subject.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const form = new FormData();
      form.set("subject_id", subjectId);
      if (params.get("topic_id")) form.set("topic_id", params.get("topic_id")!);
      if (description) form.set("description", description);
      files.forEach((f) => form.append("images", f));

      const thread = await apiFetch<QuestionThread>("/question-threads", { method: "POST", body: form }, true);
      router.push(`/ask/${thread.id}`);
    } catch {
      setError("Couldn't submit your question. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Ask a question</h1>
      <p className="mt-1 text-sm text-slate-600">
        Stuck on a question? Upload a photo and describe what you&apos;re stuck on — students and teachers can help.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="subject" className="text-sm font-medium text-slate-700">
            Subject
          </label>
          <select
            id="subject"
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
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

        <div className="flex flex-col gap-1.5">
          <label htmlFor="description" className="text-sm font-medium text-slate-700">
            Describe your question (optional)
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            placeholder="e.g. I don't understand how to complete the square in step 2."
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="images" className="text-sm font-medium text-slate-700">
            Photo of the question (optional)
          </label>
          <input
            id="images"
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            className="text-sm"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Button type="submit" disabled={submitting} className="mt-2">
          {submitting ? "Submitting…" : "Submit question"}
        </Button>
      </form>
    </main>
  );
}
