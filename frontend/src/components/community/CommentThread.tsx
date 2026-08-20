"use client";

import { useEffect, useState } from "react";
import { CommentItem } from "@/components/community/CommentItem";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Comment } from "@/types";

interface CommentThreadProps {
  contextId: string;
  contextField: "discussion_id" | "question_thread_id";
  fetchUrl: string;
}

export function CommentThread({ contextId, contextField, fetchUrl }: CommentThreadProps) {
  const { user } = useAuth();
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    apiFetch<Comment[]>(fetchUrl, undefined, true)
      .then(setComments)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [fetchUrl]);

  async function submitComment() {
    if (!body.trim()) return;
    setSubmitting(true);
    try {
      await apiFetch("/comments", { method: "POST", body: JSON.stringify({ [contextField]: contextId, body }) }, true);
      setBody("");
      refresh();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      {user && (
        <div className="flex flex-col gap-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            placeholder="Ask a follow-up question or share what you think…"
            className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          />
          <button
            onClick={submitComment}
            disabled={submitting || !body.trim()}
            className="self-start rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            Post
          </button>
        </div>
      )}

      <div className="mt-6 flex flex-col gap-4">
        {loading && <p className="text-sm text-slate-500">Loading comments…</p>}
        {!loading && comments.length === 0 && <p className="text-sm text-slate-500">No comments yet — be the first to reply.</p>}
        {comments.map((comment) => (
          <CommentItem key={comment.id} comment={comment} contextId={contextId} contextField={contextField} onChanged={refresh} />
        ))}
      </div>
    </div>
  );
}
