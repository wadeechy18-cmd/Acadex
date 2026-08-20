"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Comment } from "@/types";

interface CommentItemProps {
  comment: Comment;
  contextId: string;
  contextField: "discussion_id" | "question_thread_id";
  onChanged: () => void;
  depth?: number;
}

export function CommentItem({ comment, contextId, contextField, onChanged, depth = 0 }: CommentItemProps) {
  const { user } = useAuth();
  const [replying, setReplying] = useState(false);
  const [replyBody, setReplyBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canModerate = user && (user.role === "admin" || user.role === "teacher");
  const isOwnComment = user?.id === comment.author.id;

  async function submitReply() {
    if (!replyBody.trim()) return;
    setSubmitting(true);
    try {
      await apiFetch(
        "/comments",
        {
          method: "POST",
          body: JSON.stringify({ [contextField]: contextId, parent_comment_id: comment.id, body: replyBody }),
        },
        true
      );
      setReplyBody("");
      setReplying(false);
      onChanged();
    } finally {
      setSubmitting(false);
    }
  }

  async function vote(value: number) {
    if (!user) return;
    await apiFetch(`/comments/${comment.id}/vote`, { method: "POST", body: JSON.stringify({ value }) }, true);
    onChanged();
  }

  async function togglePin() {
    await apiFetch(`/comments/${comment.id}/pin`, { method: "POST" }, true);
    onChanged();
  }

  async function toggleVerified() {
    await apiFetch(`/comments/${comment.id}/verify`, { method: "POST" }, true);
    onChanged();
  }

  async function remove() {
    await apiFetch(`/comments/${comment.id}`, { method: "DELETE" }, true);
    onChanged();
  }

  return (
    <div className={depth > 0 ? "ml-6 border-l border-slate-200 pl-4" : ""}>
      <div className={`rounded-lg p-4 ${comment.is_pinned ? "bg-amber-50" : "bg-slate-50"}`}>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className="font-semibold text-slate-800">{comment.author.display_name}</span>
          {comment.author.role === "teacher" && comment.author.is_verified_teacher && (
            <span className="rounded-full bg-brand-100 px-2 py-0.5 font-medium text-brand-700">Verified Teacher</span>
          )}
          {comment.is_verified_teacher_answer && (
            <span className="rounded-full bg-green-100 px-2 py-0.5 font-medium text-green-700">
              Verified Teacher Answer
            </span>
          )}
          {comment.is_pinned && <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-700">Pinned</span>}
          <span>· {new Date(comment.created_at).toLocaleDateString()}</span>
        </div>
        <p className="mt-2 text-sm text-slate-800">{comment.body}</p>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
          <button onClick={() => vote(comment.my_vote === 1 ? 0 : 1)} className={`font-medium ${comment.my_vote === 1 ? "text-brand-700" : "text-slate-500"}`}>
            ▲ Upvote
          </button>
          <span className="text-slate-500">{comment.vote_score}</span>
          <button onClick={() => vote(comment.my_vote === -1 ? 0 : -1)} className={`font-medium ${comment.my_vote === -1 ? "text-red-700" : "text-slate-500"}`}>
            ▼ Downvote
          </button>
          {user && (
            <button onClick={() => setReplying((r) => !r)} className="font-medium text-slate-500 hover:text-slate-800">
              Reply
            </button>
          )}
          {canModerate && (
            <button onClick={togglePin} className="font-medium text-slate-500 hover:text-slate-800">
              {comment.is_pinned ? "Unpin" : "Pin"}
            </button>
          )}
          {user?.role === "teacher" && isOwnComment && (
            <button onClick={toggleVerified} className="font-medium text-slate-500 hover:text-slate-800">
              {comment.is_verified_teacher_answer ? "Unmark verified" : "Mark as verified answer"}
            </button>
          )}
          {(isOwnComment || user?.role === "admin") && !comment.is_deleted && (
            <button onClick={remove} className="font-medium text-red-500 hover:text-red-700">
              Delete
            </button>
          )}
        </div>

        {replying && (
          <div className="mt-3 flex flex-col gap-2">
            <textarea
              value={replyBody}
              onChange={(e) => setReplyBody(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              placeholder="Write a reply…"
            />
            <div className="flex gap-2">
              <button
                onClick={submitReply}
                disabled={submitting || !replyBody.trim()}
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Post reply
              </button>
              <button onClick={() => setReplying(false)} className="text-xs font-medium text-slate-500">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {comment.replies.length > 0 && (
        <div className="mt-3 flex flex-col gap-3">
          {comment.replies.map((reply) => (
            <CommentItem
              key={reply.id}
              comment={reply}
              contextId={contextId}
              contextField={contextField}
              onChanged={onChanged}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
