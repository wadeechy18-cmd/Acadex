import Link from "next/link";
import { Button } from "@/components/ui/Button";

const FEATURES = [
  { title: "Video lessons", body: "Clear, topic-by-topic video walkthroughs you can pause, rewind, and resume." },
  { title: "Written notes", body: "Exam-focused notes with formulas, worked examples, and key points." },
  { title: "Practice questions", body: "Filter by topic, difficulty, and exam board to build real exam skill." },
  { title: "Quizzes", body: "Auto-marked quizzes with instant feedback and score history." },
  { title: "Ask a question", body: "Stuck on a question? Photograph it and get help from the community." },
  { title: "Teacher support", body: "Verified teachers answer questions and pin the best explanations." },
];

const LEVELS = [
  { name: "GCSE", subjects: "Mathematics · Physics · Chemistry" },
  { name: "International A-Level", subjects: "Mathematics · Physics · Chemistry" },
  { name: "University — Year 1 CS", subjects: "Programming · Data Structures · Databases · and more" },
];

export default function LandingPage() {
  return (
    <main>
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="text-xl font-bold text-brand-700">Acadex</span>
        <nav className="flex items-center gap-3">
          <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-slate-900">
            Log in
          </Link>
          <Button variant="primary" className="text-sm">
            Start Learning
          </Button>
        </nav>
      </header>

      <section className="mx-auto max-w-4xl px-6 py-20 text-center">
        <span className="inline-block rounded-full bg-brand-50 px-4 py-1 text-sm font-medium text-brand-700">
          100% free while we build
        </span>
        <h1 className="mt-6 text-5xl font-extrabold tracking-tight text-slate-900">
          Learn. Practice. Ask. Improve.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600">
          Video lessons, notes, practice questions, quizzes, past papers, and a
          community of students and teachers — everything you need for GCSE,
          International A-Level, and first-year Computer Science, in one place.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Button variant="primary">Start Learning</Button>
          <Button variant="secondary">Explore Subjects</Button>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-center text-2xl font-bold text-slate-900">Built for your level</h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-3">
          {LEVELS.map((level) => (
            <div key={level.name} className="rounded-xl border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-900">{level.name}</h3>
              <p className="mt-2 text-sm text-slate-600">{level.subjects}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-center text-2xl font-bold text-slate-900">Everything you need to learn</h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <div key={feature.title} className="rounded-xl bg-slate-50 p-6">
              <h3 className="font-semibold text-slate-900">{feature.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{feature.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-slate-200 py-10 text-center text-sm text-slate-500">
        © {new Date().getFullYear()} Acadex. Currently free for everyone.
      </footer>
    </main>
  );
}
