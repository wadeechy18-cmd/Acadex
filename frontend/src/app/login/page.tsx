"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <Link href="/" className="mb-8 text-xl font-bold text-brand-700">
        Acadex
      </Link>
      <h1 className="text-2xl font-bold text-slate-900">Log in</h1>
      <p className="mt-1 text-sm text-slate-600">Welcome back. Pick up where you left off.</p>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
        <Input
          label="Email"
          type="email"
          name="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          label="Password"
          type="password"
          name="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <Button type="submit" disabled={submitting} className="mt-2">
          {submitting ? "Logging in…" : "Log in"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        New to Acadex?{" "}
        <Link href="/register" className="font-medium text-brand-700 hover:underline">
          Create an account
        </Link>
      </p>
      <p className="mt-2 text-center text-sm text-slate-600">
        <Link href="/forgot-password" className="hover:underline">
          Forgot your password?
        </Link>
      </p>
    </main>
  );
}
