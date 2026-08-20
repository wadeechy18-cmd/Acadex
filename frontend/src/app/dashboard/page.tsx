"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth-context";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

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
        <Button variant="secondary" onClick={logout}>
          Log out
        </Button>
      </div>
      <p className="mt-8 rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
        Your courses, progress, and recommended topics will appear here once subjects are published.
      </p>
    </main>
  );
}
