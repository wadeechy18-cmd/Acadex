"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { PastPaperDetail } from "@/types";

const RESOURCE_LABELS: Record<string, string> = {
  official_link: "Official link",
  licensed_document: "Licensed document",
  original_solution: "Original solution",
};

export default function PastPaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [paper, setPaper] = useState<PastPaperDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<PastPaperDetail>(`/past-papers/${id}`)
      .then(setPaper)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? "Past paper not found." : "Couldn't load this past paper."))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  if (error || !paper) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-red-600">{error ?? "Past paper not found."}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-bold text-slate-900">{paper.title}</h1>
      <p className="mt-1 text-sm text-slate-600">
        {paper.year} · Paper {paper.paper_number}
      </p>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-slate-900">Resources</h2>
        {paper.resources.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">
            No resources are available for this paper yet. Official links and licensed materials are added by
            admins once permission/licensing is confirmed.
          </p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {paper.resources.map((r) => (
              <li key={r.id} className="rounded-lg border border-slate-200 p-3 text-sm">
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {RESOURCE_LABELS[r.resource_type]}
                </span>
                <span className="ml-2 text-slate-800">{r.label}</span>
                {r.external_url && (
                  <a href={r.external_url} target="_blank" rel="noopener noreferrer" className="ml-2 text-brand-700 hover:underline">
                    Open ↗
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {paper.paper_questions.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-slate-900">Topic-tagged questions</h2>
          <p className="mt-1 text-sm text-slate-500">{paper.paper_questions.length} question(s) from this paper are available for topic practice.</p>
        </section>
      )}
    </main>
  );
}
