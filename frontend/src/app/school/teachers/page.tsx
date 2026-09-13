"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { SchoolMember } from "@/types";

export default function SchoolTeachersPage() {
  const { school } = useAuth();
  const [members, setMembers] = useState<SchoolMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [adding, setAdding] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function loadMembers() {
    if (!school) return;
    setLoading(true);
    apiFetch<SchoolMember[]>(`/schools/${school.id}/members`, undefined, true)
      .then(setMembers)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load teachers."))
      .finally(() => setLoading(false));
  }

  useEffect(loadMembers, [school]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!school) return;
    setFormError(null);
    setAdding(true);
    try {
      await apiFetch(`/schools/${school.id}/members`, { method: "POST", body: JSON.stringify({ email, role: "teacher" }) }, true);
      setEmail("");
      loadMembers();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Couldn't add that teacher.");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(memberId: string) {
    if (!school) return;
    await apiFetch(`/schools/${school.id}/members/${memberId}`, { method: "DELETE" }, true);
    loadMembers();
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Teachers</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Add a teacher who already has an Acadex account by their email.
      </p>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && (
        <div className="mt-6 flex flex-col gap-2">
          {members.map((m) => (
            <div key={m.id} className="flex items-center justify-between rounded-lg border p-4">
              <div>
                <p className="font-medium">{m.display_name}</p>
                <p className="text-sm text-muted-foreground">
                  {m.email} · {m.role}
                </p>
              </div>
              {m.role !== "admin" && (
                <Button variant="outline" size="sm" onClick={() => handleRemove(m.id)}>
                  Remove
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleAdd} className="mt-8 flex max-w-sm flex-col gap-3 border-t pt-6">
        <Label htmlFor="email">Teacher email</Label>
        <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        {formError && <p className="text-sm text-destructive">{formError}</p>}
        <Button type="submit" disabled={adding} className="self-start">
          {adding ? "Adding…" : "Add teacher"}
        </Button>
      </form>
    </main>
  );
}
