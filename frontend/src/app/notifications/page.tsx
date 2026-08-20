"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Notification } from "@/types";

export default function NotificationsPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [listLoading, setListLoading] = useState(true);

  async function refresh() {
    setNotifications(await apiFetch<Notification[]>("/notifications/me", undefined, true));
    setListLoading(false);
  }

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    async function init() {
      if (user) await refresh();
    }
    init();
  }, [user]);

  async function markRead(id: string) {
    await apiFetch(`/notifications/${id}/read`, { method: "PATCH" }, true);
    refresh();
  }

  async function markAllRead() {
    await apiFetch("/notifications/me/read-all", { method: "POST" }, true);
    refresh();
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Notifications</h1>
        <Button variant="secondary" onClick={markAllRead}>
          Mark all read
        </Button>
      </div>

      {listLoading ? (
        <p className="mt-8 text-sm text-slate-500">Loading…</p>
      ) : notifications.length === 0 ? (
        <p className="mt-8 text-sm text-slate-500">You&apos;re all caught up.</p>
      ) : (
        <div className="mt-6 flex flex-col gap-2">
          {notifications.map((n) => (
            <button
              key={n.id}
              onClick={() => !n.read_at && markRead(n.id)}
              className={`rounded-lg border p-4 text-left text-sm ${
                n.read_at ? "border-slate-200 text-slate-500" : "border-brand-200 bg-brand-50 text-slate-900"
              }`}
            >
              <p className="font-medium">{n.title}</p>
              <p className="mt-1 text-xs text-slate-500">{new Date(n.created_at).toLocaleString()}</p>
            </button>
          ))}
        </div>
      )}
    </main>
  );
}
