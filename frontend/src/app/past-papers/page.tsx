"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { PastPaper, Subject } from "@/types";

const SESSION_LABELS: Record<string, string> = {
  january: "January",
  may_june: "May/June",
  october_november: "October/November",
};

export default function PastPapersPage() {
  const [papers, setPapers] = useState<PastPaper[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectFilter, setSubjectFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Subject[]>("/subjects").then(setSubjects);
  }, []);

  useEffect(() => {
    const query = subjectFilter ? `?subject_id=${subjectFilter}` : "";
    apiFetch<PastPaper[]>(`/past-papers${query}`)
      .then(setPapers)
      .finally(() => setLoading(false));
  }, [subjectFilter]);

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Past papers</h1>
      <p className="mt-1 text-sm text-slate-600">Browse past exam paper metadata and available resources.</p>

      <div className="mt-6">
        <select
          value={subjectFilter}
          onChange={(e) => setSubjectFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <option value="">All subjects</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="mt-8 text-sm text-slate-500">Loading…</p>
      ) : papers.length === 0 ? (
        <p className="mt-8 text-sm text-slate-500">No past papers found.</p>
      ) : (
        <div className="mt-6 flex flex-col gap-3">
          {papers.map((paper) => (
            <Link
              key={paper.id}
              href={`/past-papers/${paper.id}`}
              className="flex items-center justify-between rounded-xl border border-slate-200 p-4 text-sm hover:border-brand-300 hover:bg-brand-50"
            >
              <span className="font-medium text-slate-900">{paper.title}</span>
              <span className="text-slate-500">
                {paper.year} · {SESSION_LABELS[paper.session]} · Paper {paper.paper_number}
              </span>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
