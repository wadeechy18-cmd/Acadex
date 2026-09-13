import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function StudentComingSoonPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-2xl font-bold">Coming Soon</h1>
      <p className="max-w-md text-muted-foreground">
        Student learning on Acadex isn&apos;t available yet. We&apos;re starting with tools for
        teachers and schools first.
      </p>
      <Link href="/">
        <Button variant="secondary">Back to home</Button>
      </Link>
    </main>
  );
}
