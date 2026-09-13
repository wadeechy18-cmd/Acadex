"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/teacher/dashboard", label: "Dashboard" },
  { href: "/teacher/lesson-planner", label: "Lesson Planner" },
  { href: "/teacher/lesson-plans", label: "My Lesson Plans" },
  { href: "/teacher/resources", label: "Resources" },
  { href: "/teacher/classes", label: "Classes" },
  { href: "/teacher/tasks", label: "Tasks" },
  { href: "/teacher/cover", label: "Cover" },
  { href: "/teacher/notifications", label: "Notifications" },
  { href: "/teacher/calendar", label: "Calendar" },
  { href: "/teacher/settings", label: "Settings" },
];

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && (!user || user.role !== "teacher")) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user || user.role !== "teacher") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </main>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-56 shrink-0 border-r bg-muted/30 p-4 sm:flex sm:flex-col">
        <Link href="/" className="mb-6 text-lg font-bold text-primary">
          Acadex
        </Link>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-2 text-sm font-medium ${
                pathname === item.href ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-2 pt-4">
          <p className="truncate text-xs text-muted-foreground">{user.display_name}</p>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </aside>
      <div className="flex-1">{children}</div>
    </div>
  );
}
