"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { DashboardSummary } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    async function loadSummary() {
      if (!user || user.role !== "student") return;
      setSummary(await apiFetch<DashboardSummary>("/dashboard/me", undefined, true));
    }

    loadSummary().finally(() => setSummaryLoading(false));
  }, [user]);

  if (loading || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Welcome back, {user.display_name.split(" ")[0]}</h1>
          <p className="mt-1 text-sm capitalize text-slate-600">{user.role} account</p>
        </div>
        <div className="flex items-center gap-3">
          {user.role === "student" && (
            <Link href="/ask">
              <Button variant="primary">Ask a question</Button>
            </Link>
          )}
          <Button variant="secondary" onClick={logout}>
            Log out
          </Button>
        </div>
      </div>

      {user.role !== "student" ? (
        <p className="mt-8 rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          {user.role === "teacher" ? "The teacher dashboard is coming in a later milestone." : "The admin dashboard is coming in a later milestone."}
        </p>
      ) : summaryLoading ? (
        <p className="mt-8 text-sm text-slate-500">Loading your dashboard…</p>
      ) : (
        <div className="mt-8 flex flex-col gap-8">
          {summary?.continue_learning && (
            <section>
              <h2 className="text-lg font-semibold text-slate-900">Continue learning</h2>
              <div className="mt-3 rounded-xl border border-brand-200 bg-brand-50 p-5">
                <p className="font-medium text-slate-900">{summary.continue_learning.topic.title}</p>
                <p className="mt-1 text-sm text-slate-600">
                  {summary.continue_learning.completion_percentage}% complete
                </p>
              </div>
            </section>
          )}

          <section>
            <h2 className="text-lg font-semibold text-slate-900">My courses</h2>
            {summary?.my_courses.length ? (
              <div className="mt-3 flex flex-col gap-3">
                {summary.my_courses.map((enrollment) => (
                  <Link
                    key={enrollment.id}
                    href={`/courses/${enrollment.course.slug}`}
                    className="rounded-xl border border-slate-200 p-5 transition-colors hover:border-brand-300 hover:bg-brand-50"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-slate-900">{enrollment.course.title}</h3>
                      <span className="text-sm text-slate-500">{enrollment.completion_percentage}%</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full bg-brand-500"
                        style={{ width: `${enrollment.completion_percentage}%` }}
                      />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="mt-3 rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
                You haven&apos;t enrolled in any courses yet.{" "}
                <Link href="/subjects" className="text-brand-700 hover:underline">
                  Explore subjects
                </Link>
                .
              </p>
            )}
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-900">Bookmarks</h2>
            {summary?.bookmarks.length ? (
              <p className="mt-3 text-sm text-slate-600">{summary.bookmarks.length} saved item(s).</p>
            ) : (
              <p className="mt-3 text-sm text-slate-500">Nothing bookmarked yet.</p>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
