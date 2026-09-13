"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

interface AuditLogEntry {
  id: string;
  actor_name: string;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
}

const ACTION_LABELS: Record<string, string> = {
  "member.add": "Added a teacher",
  "member.remove": "Removed a teacher",
  "task.create": "Created a task",
  "task.update": "Updated a task",
  "task.delete": "Deleted a task",
  "absence.report": "Reported an absence",
  "absence.delete": "Deleted an absence",
  "timetable_entry.create": "Added a timetable entry",
  "timetable_entry.update": "Edited a timetable entry",
  "timetable_entry.delete": "Removed a timetable entry",
  "substitution_plan.approve": "Approved a cover plan",
  "substitution_plan.reject": "Rejected a cover plan",
  "substitution_assignment.reassign": "Reassigned cover",
};

export default function SchoolSettingsPage() {
  const { school } = useAuth();
  const [log, setLog] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!school) return;
    apiFetch<AuditLogEntry[]>(`/schools/${school.id}/audit-log`, undefined, true)
      .then(setLog)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load the audit log."))
      .finally(() => setLoading(false));
  }, [school]);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">School Settings</h1>
      {school && (
        <p className="mt-1 text-sm text-muted-foreground">
          {school.name} · your role: {school.my_role}
        </p>
      )}

      <h2 className="mt-8 text-lg font-semibold">Audit log</h2>
      <p className="mt-1 text-sm text-muted-foreground">A record of admin actions taken in this school.</p>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}
      {!loading && !error && log.length === 0 && <p className="mt-6 text-sm text-muted-foreground">No actions recorded yet.</p>}

      {!loading && !error && log.length > 0 && (
        <div className="mt-4 flex flex-col gap-2">
          {log.map((entry) => (
            <div key={entry.id} className="rounded-md border p-3 text-sm">
              <p className="font-medium">{ACTION_LABELS[entry.action] ?? entry.action}</p>
              <p className="text-muted-foreground">
                {entry.actor_name} · {new Date(entry.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
