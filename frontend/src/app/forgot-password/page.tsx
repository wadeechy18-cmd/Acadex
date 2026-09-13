"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [devToken, setDevToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await apiFetch<{ detail: string; reset_token: string | null }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(res.detail);
      setDevToken(res.reset_token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <Link href="/" className="mb-8 text-xl font-bold text-primary">
        Acadex
      </Link>
      <h1 className="text-2xl font-bold">Reset your password</h1>

      {!message ? (
        <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" disabled={submitting} className="mt-2">
            {submitting ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      ) : (
        <div className="mt-8 flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">{message}</p>
          {devToken && (
            <div className="rounded-md border bg-muted p-3 text-xs">
              <p className="font-medium">No email service is configured yet, so here&apos;s your reset link (development only):</p>
              <Link href={`/reset-password?token=${devToken}`} className="mt-2 block break-all text-primary underline">
                /reset-password?token={devToken}
              </Link>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
