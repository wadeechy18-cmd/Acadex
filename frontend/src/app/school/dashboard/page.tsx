"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";

export default function SchoolDashboardPage() {
  const { user, school } = useAuth();

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Welcome, {user?.display_name}</h1>
      <p className="mt-1 text-sm text-muted-foreground">{school?.name}</p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Teachers</CardTitle>
            <CardDescription>Add and manage the teachers at your school.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/school/teachers">
              <Button size="sm">Manage teachers</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
