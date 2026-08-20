import type { QuestionSafe } from "@/types";

interface QuestionInputProps {
  question: QuestionSafe;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function QuestionInput({ question, value, onChange, disabled }: QuestionInputProps) {
  if (question.question_type === "mcq" || question.question_type === "true_false") {
    return (
      <div className="flex flex-col gap-2">
        {question.options.map((option) => (
          <label
            key={option.id}
            className={`flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-2.5 text-sm transition-colors ${
              value === option.id ? "border-brand-500 bg-brand-50" : "border-slate-200 hover:bg-slate-50"
            }`}
          >
            <input
              type="radio"
              name={question.id}
              value={option.id}
              checked={value === option.id}
              onChange={(e) => onChange(e.target.value)}
              disabled={disabled}
              className="h-4 w-4 accent-brand-600"
            />
            {option.text}
          </label>
        ))}
      </div>
    );
  }

  if (question.question_type === "numerical") {
    return (
      <input
        type="text"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder="Enter a numerical answer"
        className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      />
    );
  }

  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      rows={4}
      placeholder="Write your answer…"
      className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    />
  );
}
