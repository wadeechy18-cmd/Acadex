"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { Organization } from "@/types";

export default function PlannerWorkspacesPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "teacher")) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user || user.role !== "teacher") return;
    apiFetch<Organization[]>("/organizations/me", undefined, true)
      .then(setOrganizations)
      .catch(() => setError("Couldn't load your workspaces."))
      .finally(() => setDataLoading(false));
  }, [user]);

  if (loading || !user) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Your workspaces</h1>
        <Link href="/teacher" className="text-sm font-medium text-brand-700 hover:underline">
          Content dashboard →
        </Link>
      </div>
      <p className="mt-1 text-sm text-slate-600">
        Your personal workspace is private to you. A school workspace is shared with the other teachers there.
      </p>

      {dataLoading && <p className="mt-8 text-sm text-slate-500">Loading…</p>}
      {error && <p className="mt-8 text-sm text-red-600">{error}</p>}

      {!dataLoading && !error && (
        <div className="mt-8 flex flex-col gap-3">
          {organizations.map((org) => (
            <div key={org.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-5">
              <Link href={`/planner/${org.id}/classes`} className="flex-1 hover:text-brand-700">
                <h2 className="font-semibold text-slate-900">{org.name}</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {org.kind === "personal" ? "Personal workspace" : "School"} · your role: {org.my_role}
                </p>
              </Link>
              <div className="flex items-center gap-3">
                <Link href={`/planner/${org.id}/resources`} className="text-sm font-medium text-brand-700 hover:underline">
                  Resources
                </Link>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium capitalize text-slate-600">
                  {org.kind}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="mt-10 rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
        Click a workspace to manage its classes. Lesson planning and weekly schedules land here in upcoming phases.
      </p>
    </main>
  );
}
