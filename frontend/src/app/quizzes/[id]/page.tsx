"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { QuestionInput } from "@/components/practice/QuestionInput";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { QuizAttempt, QuizAttemptResult, QuizDetail } from "@/types";

export default function QuizPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [result, setResult] = useState<QuizAttemptResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    apiFetch<QuizDetail>(`/quizzes/${id}`)
      .then(setQuiz)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? "Quiz not found." : "Couldn't load this quiz."))
      .finally(() => setLoading(false));
  }, [id]);

  async function startQuiz() {
    if (user && user.role === "student") {
      const attemptRes = await apiFetch<QuizAttempt>(`/quizzes/${id}/attempts`, { method: "POST" }, true);
      setAttempt(attemptRes);
    }
    setStarted(true);
  }

  async function handleSubmit() {
    if (!quiz) return;
    setSubmitting(true);
    try {
      const payload = {
        answers: quiz.questions.map((q) => ({ question_id: q.id, answer: answers[q.id] ?? "" })),
      };
      const res = attempt
        ? await apiFetch<QuizAttemptResult>(
            `/quiz-attempts/${attempt.id}/submit`,
            { method: "POST", body: JSON.stringify(payload) },
            true
          )
        : await apiFetch<QuizAttemptResult>(`/quizzes/${id}/check`, {
            method: "POST",
            body: JSON.stringify(payload),
          });
      setResult(res);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  if (error || !quiz) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-red-600">{error ?? "Quiz not found."}</p>
      </main>
    );
  }

  if (result) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <h1 className="text-2xl font-bold text-slate-900">{quiz.title} — results</h1>
        <p className="mt-2 text-lg text-slate-700">
          Score: {result.score} ({result.percentage}%)
        </p>
        <div className="mt-6 flex flex-col gap-4">
          {quiz.questions.map((q) => {
            const r = result.answers.find((a) => a.question_id === q.id);
            const studentAnswerDisplay =
              (q.question_type === "mcq" || q.question_type === "true_false") && r?.student_answer
                ? (q.options.find((o) => o.id === r.student_answer)?.text ?? r.student_answer)
                : r?.student_answer;
            return (
              <div key={q.id} className="rounded-lg border border-slate-200 p-4">
                <p className="text-sm font-medium text-slate-900">{q.prompt}</p>
                <p className={`mt-1 text-sm ${r?.is_correct ? "text-green-700" : "text-red-700"}`}>
                  Your answer: {studentAnswerDisplay || "(no answer)"}{" "}
                  {r?.is_correct === true ? "✓" : r?.is_correct === false ? "✗" : ""}
                </p>
                {r?.is_correct === false && r.correct_answer && (
                  <p className="mt-1 text-sm text-slate-600">Correct answer: {r.correct_answer}</p>
                )}
                {r?.explanation && <p className="mt-1 text-sm text-slate-500">{r.explanation}</p>}
              </div>
            );
          })}
        </div>
      </main>
    );
  }

  if (!started) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <h1 className="text-2xl font-bold text-slate-900">{quiz.title}</h1>
        <p className="mt-2 text-slate-600">
          {quiz.questions.length} question{quiz.questions.length !== 1 ? "s" : ""}
          {quiz.has_timer && quiz.time_limit_seconds ? ` · ${Math.round(quiz.time_limit_seconds / 60)} min` : ""}
        </p>
        {!user && (
          <p className="mt-2 text-sm text-slate-500">
            No account needed — take the quiz and see your score right away.
          </p>
        )}
        <Button className="mt-6" onClick={startQuiz}>
          Start quiz
        </Button>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-bold text-slate-900">{quiz.title}</h1>
      <div className="mt-6 flex flex-col gap-8">
        {quiz.questions.map((q, i) => (
          <div key={q.id}>
            <p className="text-sm font-medium text-slate-900">
              {i + 1}. {q.prompt}
            </p>
            <div className="mt-3">
              <QuestionInput
                question={q}
                value={answers[q.id] ?? ""}
                onChange={(value) => setAnswers((prev) => ({ ...prev, [q.id]: value }))}
              />
            </div>
          </div>
        ))}
      </div>
      <Button className="mt-8" onClick={handleSubmit} disabled={submitting}>
        {submitting ? "Submitting…" : "Submit quiz"}
      </Button>
    </main>
  );
}
