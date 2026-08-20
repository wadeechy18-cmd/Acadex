"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { QuestionInput } from "@/components/practice/QuestionInput";
import { apiFetch } from "@/lib/api-client";
import type { AnswerCheckResult, QuestionSafe } from "@/types";

export default function PracticePage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-2xl px-6 py-12">
          <p className="text-sm text-slate-500">Loading…</p>
        </main>
      }
    >
      <PracticePageInner />
    </Suspense>
  );
}

function PracticePageInner() {
  const params = useSearchParams();
  const topicId = params.get("topic_id");
  const subjectId = params.get("subject_id");

  const [questions, setQuestions] = useState<QuestionSafe[]>([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<AnswerCheckResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    const query = new URLSearchParams();
    if (topicId) query.set("topic_id", topicId);
    if (subjectId) query.set("subject_id", subjectId);
    apiFetch<QuestionSafe[]>(`/questions?${query.toString()}`)
      .then(setQuestions)
      .finally(() => setLoading(false));
  }, [topicId, subjectId]);

  const current = questions[index];

  async function handleCheck() {
    if (!current || !answer) return;
    setChecking(true);
    try {
      const res = await apiFetch<AnswerCheckResult>(`/questions/${current.id}/check`, {
        method: "POST",
        body: JSON.stringify({ answer }),
      });
      setResult(res);
    } finally {
      setChecking(false);
    }
  }

  function handleNext() {
    setIndex((i) => i + 1);
    setAnswer("");
    setResult(null);
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  if (questions.length === 0) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-slate-500">No practice questions are available here yet.</p>
      </main>
    );
  }

  if (!current) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <h1 className="text-2xl font-bold text-slate-900">Nice work!</h1>
        <p className="mt-2 text-slate-600">
          You&apos;ve worked through all {questions.length} question(s) in this set.
        </p>
        <Link href="/subjects" className="mt-4 inline-block text-sm text-brand-700 hover:underline">
          ← Back to subjects
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <p className="text-sm text-slate-500">
        Question {index + 1} of {questions.length} · {current.marks} mark{current.marks !== 1 ? "s" : ""} ·{" "}
        <span className="capitalize">{current.difficulty}</span>
      </p>
      <p className="mt-4 text-lg text-slate-900">{current.prompt}</p>

      <div className="mt-6">
        <QuestionInput question={current} value={answer} onChange={setAnswer} disabled={!!result} />
      </div>

      {result && (
        <div
          className={`mt-4 rounded-lg px-4 py-3 text-sm ${
            result.is_correct === true
              ? "bg-green-50 text-green-800"
              : result.is_correct === false
                ? "bg-red-50 text-red-800"
                : "bg-slate-50 text-slate-700"
          }`}
        >
          {result.is_correct === true && <p className="font-semibold">Correct!</p>}
          {result.is_correct === false && (
            <p className="font-semibold">Not quite. Correct answer: {result.correct_answer}</p>
          )}
          {result.is_correct === null && <p className="font-semibold">Answer recorded for review.</p>}
          {result.explanation && <p className="mt-1">{result.explanation}</p>}
        </div>
      )}

      <div className="mt-6 flex gap-3">
        {!result ? (
          <Button onClick={handleCheck} disabled={checking || !answer}>
            {checking ? "Checking…" : "Check answer"}
          </Button>
        ) : (
          <Button onClick={handleNext}>Next question</Button>
        )}
      </div>
    </main>
  );
}
