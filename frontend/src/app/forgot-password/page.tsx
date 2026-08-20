"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/api-client";

interface ResetRequestResponse {
  message: string;
  dev_reset_token?: string;
}

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [devToken, setDevToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleRequest(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await apiFetch<ResetRequestResponse>("/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(res.message);
      if (res.dev_reset_token) {
        // No email provider is configured yet — see docs/ARCHITECTURE.md. The API
        // returns the token directly in development so this flow is testable.
        setDevToken(res.dev_reset_token);
        setToken(res.dev_reset_token);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirm(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiFetch("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      router.push("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That reset link is invalid or has expired.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <Link href="/" className="mb-8 text-xl font-bold text-brand-700">
        Acadex
      </Link>
      <h1 className="text-2xl font-bold text-slate-900">Reset your password</h1>

      {!message ? (
        <form onSubmit={handleRequest} className="mt-8 flex flex-col gap-4">
          <p className="text-sm text-slate-600">Enter your email and we&apos;ll send you a reset link.</p>
          <Input
            label="Email"
            type="email"
            name="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
          <Button type="submit" disabled={submitting} className="mt-2">
            {submitting ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      ) : (
        <form onSubmit={handleConfirm} className="mt-8 flex flex-col gap-4">
          <p className="text-sm text-slate-600">{message}</p>
          {devToken && (
            <p className="rounded-lg bg-amber-50 px-3.5 py-2.5 text-xs text-amber-800">
              Email delivery isn&apos;t wired up yet, so in development the reset token is pre-filled below.
            </p>
          )}
          <Input label="Reset token" name="token" required value={token} onChange={(e) => setToken(e.target.value)} />
          <Input
            label="New password"
            type="password"
            name="newPassword"
            autoComplete="new-password"
            minLength={8}
            maxLength={72}
            required
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
          <Button type="submit" disabled={submitting} className="mt-2">
            {submitting ? "Resetting…" : "Reset password"}
          </Button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-slate-600">
        <Link href="/login" className="font-medium text-brand-700 hover:underline">
          Back to log in
        </Link>
      </p>
    </main>
  );
}
