"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { PastPaper, PastPaperSessionType, Subject } from "@/types";

const SESSIONS: PastPaperSessionType[] = ["january", "may_june", "october_november"];

export default function AdminPastPapersPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [papers, setPapers] = useState<PastPaper[]>([]);

  const [subjectId, setSubjectId] = useState("");
  const [title, setTitle] = useState("");
  const [year, setYear] = useState(new Date().getFullYear().toString());
  const [session, setSession] = useState<PastPaperSessionType>("may_june");
  const [paperNumber, setPaperNumber] = useState("1");
  const [creating, setCreating] = useState(false);

  const [resourcePaperId, setResourcePaperId] = useState("");
  const [resourceLabel, setResourceLabel] = useState("");
  const [resourceUrl, setResourceUrl] = useState("");
  const [resourceType, setResourceType] = useState<"official_link" | "licensed_document" | "original_solution">(
    "official_link"
  );
  const [addingResource, setAddingResource] = useState(false);

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) router.replace("/dashboard");
  }, [loading, user, router]);

  async function loadData() {
    const [s, p] = await Promise.all([apiFetch<Subject[]>("/subjects"), apiFetch<PastPaper[]>("/past-papers")]);
    setSubjects(s);
    setPapers(p);
  }

  useEffect(() => {
    async function init() {
      if (user?.role === "admin") await loadData();
    }
    init();
  }, [user]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!subjectId || !title.trim()) return;
    setCreating(true);
    try {
      await apiFetch(
        "/past-papers",
        {
          method: "POST",
          body: JSON.stringify({ subject_id: subjectId, title, year: Number(year), session, paper_number: paperNumber }),
        },
        true
      );
      setTitle("");
      loadData();
    } finally {
      setCreating(false);
    }
  }

  async function handleAddResource(e: React.FormEvent) {
    e.preventDefault();
    if (!resourcePaperId || !resourceLabel.trim()) return;
    setAddingResource(true);
    try {
      await apiFetch(
        `/past-papers/${resourcePaperId}/resources`,
        { method: "POST", body: JSON.stringify({ resource_type: resourceType, label: resourceLabel, external_url: resourceUrl || null }) },
        true
      );
      setResourceLabel("");
      setResourceUrl("");
    } finally {
      setAddingResource(false);
    }
  }

  if (loading || !user) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Manage past papers</h1>
      <p className="mt-1 text-sm text-slate-600">
        Add paper metadata, then attach only official links or content you have the rights to host.
      </p>

      <form onSubmit={handleCreate} className="mt-8 flex flex-col gap-4">
        <h2 className="font-semibold text-slate-900">Add a past paper</h2>
        <select
          value={subjectId}
          onChange={(e) => setSubjectId(e.target.value)}
          className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm"
        >
          <option value="">Select a subject</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <Input label="Title" name="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <div className="grid grid-cols-3 gap-3">
          <Input label="Year" name="year" type="number" value={year} onChange={(e) => setYear(e.target.value)} />
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-700">Session</label>
            <select
              value={session}
              onChange={(e) => setSession(e.target.value as PastPaperSessionType)}
              className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm"
            >
              {SESSIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", "/")}
                </option>
              ))}
            </select>
          </div>
          <Input label="Paper #" name="paperNumber" value={paperNumber} onChange={(e) => setPaperNumber(e.target.value)} />
        </div>
        <Button type="submit" disabled={creating} className="self-start">
          {creating ? "Adding…" : "Add past paper"}
        </Button>
      </form>

      <form onSubmit={handleAddResource} className="mt-10 flex flex-col gap-4 border-t border-slate-200 pt-6">
        <h2 className="font-semibold text-slate-900">Add a resource to an existing paper</h2>
        <select
          value={resourcePaperId}
          onChange={(e) => setResourcePaperId(e.target.value)}
          className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm"
        >
          <option value="">Select a paper</option>
          {papers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title}
            </option>
          ))}
        </select>
        <select
          value={resourceType}
          onChange={(e) => setResourceType(e.target.value as typeof resourceType)}
          className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm"
        >
          <option value="official_link">Official link</option>
          <option value="licensed_document">Licensed document</option>
          <option value="original_solution">Original solution</option>
        </select>
        <Input label="Label" name="resourceLabel" value={resourceLabel} onChange={(e) => setResourceLabel(e.target.value)} />
        <Input label="URL (optional)" name="resourceUrl" value={resourceUrl} onChange={(e) => setResourceUrl(e.target.value)} />
        <Button type="submit" disabled={addingResource} className="self-start">
          {addingResource ? "Adding…" : "Add resource"}
        </Button>
      </form>
    </main>
  );
}
