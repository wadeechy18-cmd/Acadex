"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { SearchResponse, SearchResult } from "@/types";

const TYPE_LABELS: Record<SearchResult["type"], string> = {
  subject: "Subject",
  course: "Course",
  lesson: "Lesson",
  past_paper: "Past paper",
};

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-2xl px-6 py-12">
          <p className="text-sm text-slate-500">Loading…</p>
        </main>
      }
    >
      <SearchPageInner />
    </Suspense>
  );
}

function SearchPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const initialQuery = params.get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!initialQuery) return;
    apiFetch<SearchResponse>(`/search?q=${encodeURIComponent(initialQuery)}`)
      .then((res) => setResults(res.results))
      .finally(() => setLoading(false));
  }, [initialQuery]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    router.push(`/search?q=${encodeURIComponent(query)}`);
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Search</h1>
      <form onSubmit={handleSubmit} className="mt-6 flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search subjects, courses, lessons, past papers…"
          className="flex-1 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        />
        <button type="submit" className="rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700">
          Search
        </button>
      </form>

      {loading && <p className="mt-8 text-sm text-slate-500">Searching…</p>}

      {!loading && initialQuery && results.length === 0 && (
        <p className="mt-8 text-sm text-slate-500">No results for &quot;{initialQuery}&quot;.</p>
      )}

      <div className="mt-8 flex flex-col gap-2">
        {results.map((r) => (
          <Link
            key={`${r.type}-${r.id}`}
            href={r.url}
            className="flex items-center justify-between rounded-lg border border-slate-200 p-4 text-sm hover:border-brand-300 hover:bg-brand-50"
          >
            <span className="font-medium text-slate-900">{r.title}</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">{TYPE_LABELS[r.type]}</span>
          </Link>
        ))}
      </div>
    </main>
  );
}
