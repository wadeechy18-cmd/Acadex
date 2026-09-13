"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { ClassSummary } from "@/types";

export default function TeacherClassesPage() {
  const [classes, setClasses] = useState<ClassSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  function loadClasses() {
    setLoading(true);
    apiFetch<ClassSummary[]>("/classes", undefined, true)
      .then(setClasses)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load classes."))
      .finally(() => setLoading(false));
  }

  useEffect(loadClasses, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await apiFetch("/classes", { method: "POST", body: JSON.stringify({ name }) }, true);
      setName("");
      loadClasses();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create that class.");
    } finally {
      setCreating(false);
    }
  }

  async function submitRename(id: string) {
    if (!renameValue.trim()) return;
    await apiFetch(`/classes/${id}`, { method: "PATCH", body: JSON.stringify({ name: renameValue }) }, true);
    setRenamingId(null);
    loadClasses();
  }

  async function handleDelete(id: string) {
    await apiFetch(`/classes/${id}`, { method: "DELETE" }, true);
    loadClasses();
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Classes</h1>
      <p className="mt-1 text-sm text-muted-foreground">Create classes you can assign lesson plans to.</p>

      <form onSubmit={handleCreate} className="mt-6 flex max-w-sm gap-2">
        <Input placeholder="e.g. Year 7A" value={name} onChange={(e) => setName(e.target.value)} />
        <Button type="submit" disabled={creating}>
          Add class
        </Button>
      </form>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && classes.length === 0 && (
        <p className="mt-8 text-sm text-muted-foreground">No classes yet.</p>
      )}

      {!loading && !error && classes.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {classes.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-lg border p-4">
              {renamingId === c.id ? (
                <div className="flex items-center gap-2">
                  <Input value={renameValue} onChange={(e) => setRenameValue(e.target.value)} className="h-8" autoFocus />
                  <Button size="sm" onClick={() => submitRename(c.id)}>
                    Save
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setRenamingId(null)}>
                    Cancel
                  </Button>
                </div>
              ) : (
                <p className="font-medium">{c.name}</p>
              )}
              {renamingId !== c.id && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setRenamingId(c.id);
                      setRenameValue(c.name);
                    }}
                  >
                    Rename
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleDelete(c.id)}>
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
