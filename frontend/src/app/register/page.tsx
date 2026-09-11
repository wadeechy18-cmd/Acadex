"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

type Onboarding = "student" | "individual_teacher" | "school";

const ONBOARDING_OPTIONS: { value: Onboarding; label: string }[] = [
  { value: "student", label: "Student" },
  { value: "individual_teacher", label: "Individual Teacher" },
  { value: "school", label: "School" },
];

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [onboarding, setOnboarding] = useState<Onboarding>("student");
  const [schoolName, setSchoolName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const role = onboarding === "student" ? "student" : "teacher";
      await register({
        email,
        password,
        displayName,
        role,
        schoolName: onboarding === "school" ? schoolName : undefined,
      });
      router.push(onboarding === "student" ? "/dashboard" : "/planner");
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
      <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
      <p className="mt-1 text-sm text-slate-600">100% free — start learning in under a minute.</p>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
        <fieldset className="flex gap-2">
          <legend className="mb-1.5 text-sm font-medium text-slate-700">I am a</legend>
          {ONBOARDING_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setOnboarding(option.value)}
              className={`flex-1 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors ${
                onboarding === option.value
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-slate-300 text-slate-600 hover:bg-slate-50"
              }`}
              aria-pressed={onboarding === option.value}
            >
              {option.label}
            </button>
          ))}
        </fieldset>

        {onboarding === "school" && (
          <Input
            label="School name"
            name="schoolName"
            required
            value={schoolName}
            onChange={(e) => setSchoolName(e.target.value)}
          />
        )}

        <Input
          label="Full name"
          name="displayName"
          autoComplete="name"
          required
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
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
          autoComplete="new-password"
          minLength={8}
          maxLength={72}
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
          {submitting ? "Creating account…" : onboarding === "student" ? "Start Learning" : "Create workspace"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-brand-700 hover:underline">
          Log in
        </Link>
      </p>
    </main>
  );
}
