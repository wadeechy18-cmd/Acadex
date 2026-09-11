"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { TeachingClass, YearGroup } from "@/types";

const YEAR_GROUP_OPTIONS: { value: YearGroup; label: string }[] = [
  { value: "nursery", label: "Nursery (EYFS)" },
  { value: "reception", label: "Reception (EYFS)" },
  { value: "year_1", label: "Year 1 (KS1)" },
  { value: "year_2", label: "Year 2 (KS1)" },
  { value: "year_3", label: "Year 3 (KS2)" },
  { value: "year_4", label: "Year 4 (KS2)" },
  { value: "year_5", label: "Year 5 (KS2)" },
  { value: "year_6", label: "Year 6 (KS2)" },
  { value: "year_7", label: "Year 7 (KS3)" },
  { value: "year_8", label: "Year 8 (KS3)" },
  { value: "year_9", label: "Year 9 (KS3)" },
  { value: "year_10", label: "Year 10 (KS4)" },
  { value: "year_11", label: "Year 11 (KS4)" },
  { value: "year_12", label: "Year 12 (KS5)" },
  { value: "year_13", label: "Year 13 (KS5)" },
];

export default function ClassesPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [classes, setClasses] = useState<TeachingClass[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [subjectName, setSubjectName] = useState("");
  const [yearGroup, setYearGroup] = useState<YearGroup>("year_7");
  const [qualification, setQualification] = useState("");
  const [examBoardName, setExamBoardName] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "teacher")) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  function loadClasses() {
    setDataLoading(true);
    apiFetch<TeachingClass[]>(`/organizations/${orgId}/classes`, undefined, true)
      .then(setClasses)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load classes."))
      .finally(() => setDataLoading(false));
  }

  useEffect(() => {
    if (!user || user.role !== "teacher" || !orgId) return;
    loadClasses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, orgId]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setCreating(true);
    try {
      await apiFetch(
        `/organizations/${orgId}/classes`,
        {
          method: "POST",
          body: JSON.stringify({
            name,
            subject_name: subjectName,
            year_group: yearGroup,
            qualification: qualification || null,
            exam_board_name: examBoardName || null,
          }),
        },
        true
      );
      setName("");
      setSubjectName("");
      setQualification("");
      setExamBoardName("");
      loadClasses();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Couldn't create the class.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(classId: string) {
    await apiFetch(`/classes/${classId}`, { method: "DELETE" }, true);
    loadClasses();
  }

  if (loading || !user) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href="/planner" className="text-sm font-medium text-brand-700 hover:underline">
        ← Your workspaces
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-slate-900">Classes</h1>

      {dataLoading && <p className="mt-8 text-sm text-slate-500">Loading…</p>}
      {error && <p className="mt-8 text-sm text-red-600">{error}</p>}

      {!dataLoading && !error && (
        <div className="mt-8 flex flex-col gap-3">
          {classes.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-5">
              <div>
                <h2 className="font-semibold text-slate-900">{c.name}</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {c.subject_name} · {c.key_stage} · {YEAR_GROUP_OPTIONS.find((y) => y.value === c.year_group)?.label}
                  {c.qualification ? ` · ${c.qualification}` : ""}
                  {c.exam_board_name ? ` · ${c.exam_board_name}` : ""}
                </p>
              </div>
              {c.teacher_user_id === user.id && (
                <Button variant="secondary" className="text-sm" onClick={() => handleDelete(c.id)}>
                  Delete
                </Button>
              )}
            </div>
          ))}
          {classes.length === 0 && (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
              No classes yet — create your first one below.
            </p>
          )}
        </div>
      )}

      <section className="mt-10 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-slate-900">Create a class</h2>
        <form onSubmit={handleCreate} className="mt-4 flex flex-col gap-4 sm:max-w-md">
          <Input label="Class name" name="className" required value={name} onChange={(e) => setName(e.target.value)} />
          <Input
            label="Subject"
            name="subjectName"
            required
            placeholder="e.g. Mathematics, Chemistry, Phonics"
            value={subjectName}
            onChange={(e) => setSubjectName(e.target.value)}
          />
          <div className="flex flex-col gap-1.5">
            <label htmlFor="yearGroup" className="text-sm font-medium text-slate-700">
              Year group
            </label>
            <select
              id="yearGroup"
              value={yearGroup}
              onChange={(e) => setYearGroup(e.target.value as YearGroup)}
              className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              {YEAR_GROUP_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <Input
            label="Qualification (optional)"
            name="qualification"
            placeholder="e.g. GCSE, International A-Level"
            value={qualification}
            onChange={(e) => setQualification(e.target.value)}
          />
          <Input
            label="Exam board (optional)"
            name="examBoardName"
            placeholder="e.g. Edexcel, AQA"
            value={examBoardName}
            onChange={(e) => setExamBoardName(e.target.value)}
          />
          {formError && (
            <p role="alert" className="text-sm text-red-600">
              {formError}
            </p>
          )}
          <Button type="submit" disabled={creating} className="self-start">
            {creating ? "Creating…" : "Create class"}
          </Button>
        </form>
      </section>
    </main>
  );
}
