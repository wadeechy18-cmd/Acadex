"use client";

import { useParams } from "next/navigation";
import { CommentThread } from "@/components/community/CommentThread";

export default function DiscussionPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Discussion</h1>
      <div className="mt-6">
        <CommentThread contextId={id} contextField="discussion_id" fetchUrl={`/discussions/${id}/comments`} />
      </div>
    </main>
  );
}
