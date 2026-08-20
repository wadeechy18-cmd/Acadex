"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { EducationLevel, Subject } from "@/types";

export default function SubjectsPage() {
  const [levels, setLevels] = useState<EducationLevel[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([apiFetch<EducationLevel[]>("/education-levels"), apiFetch<Subject[]>("/subjects")])
      .then(([levelsRes, subjectsRes]) => {
        setLevels(levelsRes);
        setSubjects(subjectsRes);
      })
      .catch(() => setError("Couldn't load subjects. Please try again shortly."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <Link href="/" className="text-sm font-medium text-brand-700 hover:underline">
        ← Back home
      </Link>
      <h1 className="mt-4 text-3xl font-bold text-slate-900">Explore subjects</h1>
      <p className="mt-1 text-slate-600">Pick your level to see the subjects available.</p>

      {loading && <p className="mt-8 text-sm text-slate-500">Loading…</p>}
      {error && <p className="mt-8 text-sm text-red-600">{error}</p>}

      {!loading &&
        !error &&
        levels.map((level) => {
          const levelSubjects = subjects.filter((s) => s.education_level_id === level.id);
          if (levelSubjects.length === 0) return null;
          return (
            <section key={level.id} className="mt-10">
              <h2 className="text-xl font-semibold text-slate-900">{level.name}</h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {levelSubjects.map((subject) => (
                  <Link
                    key={subject.id}
                    href={`/subjects/${subject.slug}`}
                    className="rounded-xl border border-slate-200 p-5 transition-colors hover:border-brand-300 hover:bg-brand-50"
                  >
                    <h3 className="font-semibold text-slate-900">{subject.name}</h3>
                    {subject.description && <p className="mt-1 text-sm text-slate-600">{subject.description}</p>}
                  </Link>
                ))}
              </div>
            </section>
          );
        })}
    </main>
  );
}
