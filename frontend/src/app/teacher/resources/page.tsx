"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch, ApiError, downloadFile, getAccessToken } from "@/lib/api-client";
import type { CurriculumSummary, KeyStageSummary, Resource, SubjectSummary, YearGroupSummary } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50";

const KIND_LABELS: Record<Resource["kind"], string> = {
  pdf: "PDF",
  docx: "Word",
  pptx: "PowerPoint",
  image: "Image",
  text: "Text",
};

export default function TeacherResourcesPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadSubjectId, setUploadSubjectId] = useState("");
  const [uploadYearGroupId, setUploadYearGroupId] = useState("");
  const [subjects, setSubjects] = useState<SubjectSummary[]>([]);
  const [yearGroups, setYearGroups] = useState<YearGroupSummary[]>([]);

  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  function loadResources() {
    setLoading(true);
    apiFetch<Resource[]>("/resources", undefined, true)
      .then(setResources)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load resources."))
      .finally(() => setLoading(false));
  }

  useEffect(loadResources, []);

  useEffect(() => {
    apiFetch<CurriculumSummary[]>("/curriculum/curricula", undefined, true).then(async (curricula) => {
      const curriculum = curricula[0];
      if (!curriculum) return;
      const [subjectList, keyStages] = await Promise.all([
        apiFetch<SubjectSummary[]>(`/curriculum/curricula/${curriculum.id}/subjects`, undefined, true),
        apiFetch<KeyStageSummary[]>(`/curriculum/curricula/${curriculum.id}/key-stages`, undefined, true),
      ]);
      setSubjects(subjectList);
      const yearGroupLists = await Promise.all(
        keyStages.map((ks) => apiFetch<YearGroupSummary[]>(`/curriculum/key-stages/${ks.id}/year-groups`, undefined, true))
      );
      setYearGroups(yearGroupLists.flat());
    });
  }, []);

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;

    setUploadError(null);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (uploadSubjectId) formData.append("subject_id", uploadSubjectId);
      if (uploadYearGroupId) formData.append("year_group_id", uploadYearGroupId);
      const token = getAccessToken();
      const res = await fetch(`${API_URL}/resources`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new ApiError(res.status, body?.detail ?? "Upload failed.");
      }
      if (fileInputRef.current) fileInputRef.current.value = "";
      loadResources();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Couldn't upload that file.");
    } finally {
      setUploading(false);
    }
  }

  function startRename(resource: Resource) {
    setRenamingId(resource.id);
    setRenameValue(resource.display_name);
  }

  async function submitRename(resourceId: string) {
    if (!renameValue.trim()) return;
    await apiFetch(`/resources/${resourceId}`, { method: "PATCH", body: JSON.stringify({ display_name: renameValue }) }, true);
    setRenamingId(null);
    loadResources();
  }

  async function handleDelete(resourceId: string) {
    await apiFetch(`/resources/${resourceId}`, { method: "DELETE" }, true);
    loadResources();
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Resources</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Upload documents, slides, and images to reuse when Acadex builds your lesson plans.
      </p>

      <form onSubmit={handleUpload} className="mt-6 flex max-w-2xl flex-col gap-3">
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <Input ref={fileInputRef} type="file" accept=".pdf,.docx,.pptx,.txt,image/jpeg,image/png,image/webp,image/gif" />
          </div>
          <Button type="submit" disabled={uploading}>
            {uploading ? "Uploading…" : "Upload"}
          </Button>
        </div>
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="text-xs text-muted-foreground">Subject (optional -- helps Acadex find this later)</label>
            <select className={selectClass} value={uploadSubjectId} onChange={(e) => setUploadSubjectId(e.target.value)}>
              <option value="">Not tagged</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="text-xs text-muted-foreground">Year group (optional)</label>
            <select className={selectClass} value={uploadYearGroupId} onChange={(e) => setUploadYearGroupId(e.target.value)}>
              <option value="">Not tagged</option>
              {yearGroups.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </form>
      {uploadError && <p className="mt-2 text-sm text-destructive">{uploadError}</p>}

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && resources.length === 0 && (
        <p className="mt-8 text-sm text-muted-foreground">No resources yet. Upload your first file above.</p>
      )}

      {!loading && !error && resources.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {resources.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-lg border p-4">
              <div className="min-w-0 flex-1">
                {renamingId === r.id ? (
                  <div className="flex items-center gap-2">
                    <Input
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      className="h-8 max-w-xs"
                      autoFocus
                    />
                    <Button size="sm" onClick={() => submitRename(r.id)}>
                      Save
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setRenamingId(null)}>
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <p className="truncate font-medium">{r.display_name}</p>
                )}
                <p className="text-sm text-muted-foreground">
                  {KIND_LABELS[r.kind]} · {(r.file_size_bytes / 1024).toFixed(0)} KB
                  {r.extraction_status === "failed" && " · couldn't extract text"}
                </p>
              </div>
              {renamingId !== r.id && (
                <div className="flex shrink-0 gap-2">
                  <Button variant="outline" size="sm" onClick={() => downloadFile(`/resources/${r.id}/file`)}>
                    Download
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => startRename(r)}>
                    Rename
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleDelete(r.id)}>
                    Delete
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
