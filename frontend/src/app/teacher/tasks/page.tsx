"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Task, TaskStatus } from "@/types";

const STATUS_LABELS: Record<Task["effective_status"], string> = {
  pending: "Pending",
  in_progress: "In Progress",
  completed: "Completed",
  overdue: "Overdue",
};

const STATUS_COLORS: Record<Task["effective_status"], string> = {
  pending: "bg-muted text-muted-foreground",
  in_progress: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  overdue: "bg-destructive/10 text-destructive",
};

export default function TeacherTasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadTasks() {
    setLoading(true);
    apiFetch<Task[]>("/tasks/mine", undefined, true)
      .then(setTasks)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load tasks."))
      .finally(() => setLoading(false));
  }

  useEffect(loadTasks, []);

  async function updateStatus(id: string, status: TaskStatus) {
    await apiFetch(`/tasks/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }, true);
    loadTasks();
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Tasks</h1>
      <p className="mt-1 text-sm text-muted-foreground">Tasks your school admin has assigned to you.</p>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && tasks.length === 0 && <p className="mt-8 text-sm text-muted-foreground">No tasks assigned to you.</p>}

      {!loading && !error && tasks.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {tasks.map((t) => (
            <div key={t.id} className="flex flex-col gap-2 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium">{t.title}</p>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[t.effective_status]}`}>
                    {STATUS_LABELS[t.effective_status]}
                  </span>
                </div>
                {t.description && <p className="mt-1 text-sm text-muted-foreground">{t.description}</p>}
                <p className="mt-1 text-sm text-muted-foreground">
                  Due {t.deadline} · Priority: {t.priority}
                  {t.subject_name && ` · ${t.subject_name}`}
                  {t.class_name && ` · ${t.class_name}`}
                </p>
              </div>
              <div className="flex gap-2">
                {t.status !== "in_progress" && t.status !== "completed" && (
                  <Button variant="outline" size="sm" onClick={() => updateStatus(t.id, "in_progress")}>
                    Start
                  </Button>
                )}
                {t.status !== "completed" && (
                  <Button variant="outline" size="sm" onClick={() => updateStatus(t.id, "completed")}>
                    Mark complete
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
