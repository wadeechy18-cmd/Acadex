"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";

export default function TeacherDashboardPage() {
  const { user, school } = useAuth();

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Welcome, {user?.display_name}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {school ? `You're part of ${school.name}.` : "You're using Acadex as an individual teacher."}
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Lesson Planner</CardTitle>
            <CardDescription>Build a new lesson aligned to the English National Curriculum.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/teacher/lesson-planner">
              <Button size="sm">Start planning</Button>
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>My Lesson Plans</CardTitle>
            <CardDescription>View, edit, and export your saved lesson plans.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/teacher/lesson-plans">
              <Button size="sm" variant="secondary">
                View library
              </Button>
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Resources</CardTitle>
            <CardDescription>Upload documents to ground your lesson plans.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/teacher/resources">
              <Button size="sm" variant="secondary">
                Manage resources
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
