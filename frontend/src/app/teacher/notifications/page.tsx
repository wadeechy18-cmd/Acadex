"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Notification } from "@/types";

export default function TeacherNotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    apiFetch<Notification[]>("/notifications/mine", undefined, true)
      .then(setNotifications)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load notifications."))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function markRead(id: string) {
    await apiFetch(`/notifications/${id}/read`, { method: "PATCH" }, true);
    load();
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Notifications</h1>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}
      {!loading && !error && notifications.length === 0 && <p className="mt-8 text-sm text-muted-foreground">No notifications.</p>}

      {!loading && !error && notifications.length > 0 && (
        <div className="mt-8 flex flex-col gap-2">
          {notifications.map((n) => (
            <div key={n.id} className={`flex items-center justify-between rounded-lg border p-4 ${n.read_at ? "opacity-60" : ""}`}>
              <div>
                <p className="font-medium">{n.title}</p>
                <p className="text-sm text-muted-foreground">{n.body}</p>
              </div>
              {!n.read_at && (
                <Button variant="outline" size="sm" onClick={() => markRead(n.id)}>
                  Mark read
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
