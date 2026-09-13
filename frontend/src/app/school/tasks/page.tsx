"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { SchoolMember, Task, TaskPriority } from "@/types";

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

const STATUS_LABELS: Record<Task["effective_status"], string> = {
  pending: "Pending",
  in_progress: "In Progress",
  completed: "Completed",
  overdue: "Overdue",
};

export default function SchoolTasksPage() {
  const { school } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [members, setMembers] = useState<SchoolMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [deadline, setDeadline] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function loadTasks() {
    if (!school) return;
    setLoading(true);
    apiFetch<Task[]>(`/schools/${school.id}/tasks`, undefined, true)
      .then(setTasks)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load tasks."))
      .finally(() => setLoading(false));
  }

  useEffect(loadTasks, [school]);
  useEffect(() => {
    if (!school) return;
    apiFetch<SchoolMember[]>(`/schools/${school.id}/members`, undefined, true).then((all) =>
      setMembers(all.filter((m) => m.role === "teacher"))
    );
  }, [school]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!school || !assignedTo || !deadline) return;
    setCreating(true);
    setFormError(null);
    try {
      await apiFetch(
        `/schools/${school.id}/tasks`,
        {
          method: "POST",
          body: JSON.stringify({ title, description: description || null, assigned_to_user_id: assignedTo, deadline, priority }),
        },
        true
      );
      setTitle("");
      setDescription("");
      setAssignedTo("");
      setDeadline("");
      setPriority("medium");
      loadTasks();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Couldn't create that task.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!school) return;
    await apiFetch(`/schools/${school.id}/tasks/${id}`, { method: "DELETE" }, true);
    loadTasks();
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Tasks</h1>
      <p className="mt-1 text-sm text-muted-foreground">Assign tasks to teachers in your school.</p>

      <form onSubmit={handleCreate} className="mt-6 grid max-w-2xl grid-cols-2 gap-4">
        <div className="col-span-2">
          <Label htmlFor="title">Title</Label>
          <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </div>
        <div className="col-span-2">
          <Label htmlFor="description">Description (optional)</Label>
          <Input id="description" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="assignedTo">Assign to</Label>
          <select id="assignedTo" className={selectClass} value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)} required>
            <option value="">Select a teacher...</option>
            {members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.display_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="deadline">Deadline</Label>
          <Input id="deadline" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} required />
        </div>
        <div>
          <Label htmlFor="priority">Priority</Label>
          <select id="priority" className={selectClass} value={priority} onChange={(e) => setPriority(e.target.value as TaskPriority)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        {formError && <p className="col-span-2 text-sm text-destructive">{formError}</p>}
        <Button type="submit" disabled={creating} className="col-span-2 self-start">
          {creating ? "Assigning…" : "Assign task"}
        </Button>
      </form>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && tasks.length === 0 && <p className="mt-8 text-sm text-muted-foreground">No tasks yet.</p>}

      {!loading && !error && tasks.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {tasks.map((t) => (
            <div key={t.id} className="flex items-center justify-between rounded-lg border p-4">
              <div>
                <p className="font-medium">{t.title}</p>
                <p className="text-sm text-muted-foreground">
                  {t.assigned_to_name} · Due {t.deadline} · {t.priority} · {STATUS_LABELS[t.effective_status]}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => handleDelete(t.id)}>
                Delete
              </Button>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
