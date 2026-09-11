"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Resource, ResourceType, ResourceVisibility, YearGroup } from "@/types";

const RESOURCE_TYPE_OPTIONS: { value: ResourceType; label: string }[] = [
  { value: "exam_specification", label: "Exam Specification" },
  { value: "scheme_of_work", label: "Scheme of Work" },
  { value: "teacher_notes", label: "Teacher Notes" },
  { value: "lesson_resource", label: "Lesson Resource" },
  { value: "worksheet", label: "Worksheet" },
  { value: "past_paper", label: "Past Paper" },
  { value: "mark_scheme", label: "Mark Scheme" },
  { value: "practical_guide", label: "Practical Guide" },
  { value: "curriculum_document", label: "Curriculum Document" },
  { value: "other", label: "Other" },
];

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

export default function ResourcesPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [resources, setResources] = useState<Resource[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [resourceType, setResourceType] = useState<ResourceType>("scheme_of_work");
  const [visibility, setVisibility] = useState<ResourceVisibility>("organization");
  const [subjectName, setSubjectName] = useState("");
  const [examBoardName, setExamBoardName] = useState("");
  const [qualification, setQualification] = useState("");
  const [yearGroup, setYearGroup] = useState<YearGroup | "">("");
  const [topic, setTopic] = useState("");
  const [unit, setUnit] = useState("");
  const [uploading, setUploading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [filterSubject, setFilterSubject] = useState("");
  const [filterYearGroup, setFilterYearGroup] = useState<YearGroup | "">("");

  useEffect(() => {
    if (!loading && (!user || user.role !== "teacher")) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  function loadResources() {
    setDataLoading(true);
    const params = new URLSearchParams();
    if (filterSubject) params.set("subject_name", filterSubject);
    if (filterYearGroup) params.set("year_group", filterYearGroup);
    const qs = params.toString() ? `?${params.toString()}` : "";
    apiFetch<Resource[]>(`/organizations/${orgId}/resources${qs}`, undefined, true)
      .then(setResources)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load resources."))
      .finally(() => setDataLoading(false));
  }

  useEffect(() => {
    if (!user || user.role !== "teacher" || !orgId) return;
    loadResources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, orgId, filterSubject, filterYearGroup]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setFormError("Choose a file first.");
      return;
    }
    setFormError(null);
    setUploading(true);
    try {
      const body = new FormData();
      body.append("file", file);
      body.append("resource_type", resourceType);
      body.append("visibility", visibility);
      if (subjectName) body.append("subject_name", subjectName);
      if (examBoardName) body.append("exam_board_name", examBoardName);
      if (qualification) body.append("qualification", qualification);
      if (yearGroup) body.append("year_group", yearGroup);
      if (topic) body.append("topic", topic);
      if (unit) body.append("unit", unit);

      await apiFetch(`/organizations/${orgId}/resources`, { method: "POST", body }, true);
      setFile(null);
      setSubjectName("");
      setExamBoardName("");
      setQualification("");
      setYearGroup("");
      setTopic("");
      setUnit("");
      loadResources();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: string) {
    await apiFetch(`/resources/${id}`, { method: "DELETE" }, true);
    loadResources();
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
      <h1 className="mt-4 text-2xl font-bold text-slate-900">Resources</h1>
      <p className="mt-1 text-sm text-slate-600">
        Upload curriculum documents, schemes of work, and teaching resources (PDF, DOCX, or TXT).
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <Input
          label="Filter by subject"
          name="filterSubject"
          value={filterSubject}
          onChange={(e) => setFilterSubject(e.target.value)}
          placeholder="e.g. Chemistry"
        />
        <div className="flex flex-col gap-1.5">
          <label htmlFor="filterYearGroup" className="text-sm font-medium text-slate-700">
            Filter by year group
          </label>
          <select
            id="filterYearGroup"
            value={filterYearGroup}
            onChange={(e) => setFilterYearGroup(e.target.value as YearGroup | "")}
            className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <option value="">All year groups</option>
            {YEAR_GROUP_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {dataLoading && <p className="mt-8 text-sm text-slate-500">Loading…</p>}
      {error && <p className="mt-8 text-sm text-red-600">{error}</p>}

      {!dataLoading && !error && (
        <div className="mt-6 flex flex-col gap-3">
          {resources.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-5">
              <div>
                <h2 className="font-semibold text-slate-900">
                  {r.file_name}
                  {r.visibility === "private" && (
                    <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                      Private
                    </span>
                  )}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {RESOURCE_TYPE_OPTIONS.find((t) => t.value === r.resource_type)?.label}
                  {r.subject_name ? ` · ${r.subject_name}` : ""}
                  {r.year_group ? ` · ${YEAR_GROUP_OPTIONS.find((y) => y.value === r.year_group)?.label}` : ""}
                  {r.qualification ? ` · ${r.qualification}` : ""}
                </p>
                <p className="mt-1 text-xs">
                  {r.extraction_status === "completed" && <span className="text-green-700">Text extracted</span>}
                  {r.extraction_status === "failed" && (
                    <span className="text-red-600">Extraction failed: {r.extraction_error}</span>
                  )}
                  {r.extraction_status === "pending" && <span className="text-amber-700">Processing…</span>}
                </p>
              </div>
              {r.uploaded_by_user_id === user.id && (
                <Button variant="secondary" className="text-sm" onClick={() => handleDelete(r.id)}>
                  Delete
                </Button>
              )}
            </div>
          ))}
          {resources.length === 0 && (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
              No resources yet — upload your first one below.
            </p>
          )}
        </div>
      )}

      <section className="mt-10 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-slate-900">Upload a resource</h2>
        <form onSubmit={handleUpload} className="mt-4 flex flex-col gap-4 sm:max-w-md">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="file" className="text-sm font-medium text-slate-700">
              File (PDF, DOCX, or TXT)
            </label>
            <input
              id="file"
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-sm"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="resourceType" className="text-sm font-medium text-slate-700">
              Resource type
            </label>
            <select
              id="resourceType"
              value={resourceType}
              onChange={(e) => setResourceType(e.target.value as ResourceType)}
              className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              {RESOURCE_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <fieldset className="flex gap-2">
            <legend className="mb-1.5 text-sm font-medium text-slate-700">Visibility</legend>
            {(
              [
                { value: "organization" as const, label: "Shared with workspace" },
                { value: "private" as const, label: "Private to me" },
              ]
            ).map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setVisibility(opt.value)}
                className={`flex-1 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors ${
                  visibility === opt.value
                    ? "border-brand-600 bg-brand-50 text-brand-700"
                    : "border-slate-300 text-slate-600 hover:bg-slate-50"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </fieldset>
          <Input label="Subject (optional)" name="subjectName" value={subjectName} onChange={(e) => setSubjectName(e.target.value)} />
          <div className="flex flex-col gap-1.5">
            <label htmlFor="yearGroup" className="text-sm font-medium text-slate-700">
              Year group (optional)
            </label>
            <select
              id="yearGroup"
              value={yearGroup}
              onChange={(e) => setYearGroup(e.target.value as YearGroup | "")}
              className="rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <option value="">Not specified</option>
              {YEAR_GROUP_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <Input label="Qualification (optional)" name="qualification" value={qualification} onChange={(e) => setQualification(e.target.value)} />
          <Input label="Exam board (optional)" name="examBoardName" value={examBoardName} onChange={(e) => setExamBoardName(e.target.value)} />
          <Input label="Topic (optional)" name="topic" value={topic} onChange={(e) => setTopic(e.target.value)} />
          <Input label="Unit (optional)" name="unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
          {formError && (
            <p role="alert" className="text-sm text-red-600">
              {formError}
            </p>
          )}
          <Button type="submit" disabled={uploading} className="self-start">
            {uploading ? "Uploading…" : "Upload"}
          </Button>
        </form>
      </section>
    </main>
  );
}
