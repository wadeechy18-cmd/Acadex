"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Discussion } from "@/types";

export function TopicDiscussions({ topicId }: { topicId: string }) {
  const { user } = useAuth();
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);

  function refresh() {
    apiFetch<Discussion[]>(`/topics/${topicId}/discussions`)
      .then(setDiscussions)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [topicId]);

  async function handleCreate() {
    if (!title.trim()) return;
    setCreating(true);
    try {
      await apiFetch("/discussions", { method: "POST", body: JSON.stringify({ topic_id: topicId, title }) }, true);
      setTitle("");
      refresh();
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      {loading ? (
        <p className="text-sm text-slate-500">Loading discussions…</p>
      ) : discussions.length === 0 ? (
        <p className="text-sm text-slate-500">No discussions yet for this topic.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {discussions.map((d) => (
            <li key={d.id}>
              <Link href={`/discussions/${d.id}`} className="text-sm text-brand-700 hover:underline">
                {d.title}
              </Link>
            </li>
          ))}
        </ul>
      )}

      {user && (
        <div className="mt-4 flex gap-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Start a new discussion…"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          />
          <button
            onClick={handleCreate}
            disabled={creating || !title.trim()}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            Start
          </button>
        </div>
      )}
    </div>
  );
}
