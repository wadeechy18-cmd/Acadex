"use client";

import { Button } from "@/components/ui/Button";
import type { LessonPlanQualityReport, TimingSuggestion } from "@/types";

interface Props {
  report: LessonPlanQualityReport;
  onApplySuggestion: (suggestion: TimingSuggestion) => void;
  readOnly: boolean;
}

export function QualityPanel({ report, onApplySuggestion, readOnly }: Props) {
  const { timing, issues } = report;

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <p className={`text-sm font-medium ${timing.status === "ok" ? "text-green-700" : "text-amber-700"}`}>
        {timing.total_minutes} min planned of {timing.planned_minutes} min
        {timing.status === "under" && ` — ${timing.difference_minutes} min remaining`}
        {timing.status === "over" && ` — ${-timing.difference_minutes} min over`}
      </p>

      {!readOnly && timing.suggestions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {timing.suggestions.map((s, i) => (
            <Button key={i} variant="secondary" className="text-xs" onClick={() => onApplySuggestion(s)}>
              {s.label}
            </Button>
          ))}
        </div>
      )}

      {issues.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1.5">
          {issues.map((issue, i) => (
            <li
              key={i}
              className={`text-xs ${issue.severity === "warning" ? "text-amber-700" : "text-slate-500"}`}
            >
              {issue.severity === "warning" ? "⚠ " : "ℹ "}
              {issue.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
