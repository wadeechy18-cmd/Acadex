"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { LessonPlanContent, Resource } from "@/types";

interface Props {
  lessonPlanId: string;
  resources: Resource[];
  onApply: (content: LessonPlanContent) => void;
}

export function AIEnhancePanel({ lessonPlanId, resources, onApply }: Props) {
  const [open, setOpen] = useState(false);
  const [instructions, setInstructions] = useState("");
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<LessonPlanContent | null>(null);

  function toggleResource(id: string) {
    setSelectedResourceIds((prev) => (prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]));
  }

  async function handleGenerate() {
    setError(null);
    setLoading(true);
    setSuggestion(null);
    try {
      const content = await apiFetch<LessonPlanContent>(
        `/lesson-plans/${lessonPlanId}/ai-enhance`,
        {
          method: "POST",
          body: JSON.stringify({ instructions: instructions || undefined, resource_ids: selectedResourceIds }),
        },
        true
      );
      setSuggestion(content);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setError("AI features aren't configured for this deployment yet.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError(err.message);
      } else {
        setError(err instanceof ApiError ? err.message : "Something went wrong.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-sm font-semibold text-slate-900"
      >
        ✨ AI Enhance {open ? "▲" : "▼"}
      </button>

      {open && (
        <div className="mt-3 flex flex-col gap-3">
          <p className="text-xs text-slate-500">
            Optional -- the local planning engine already works without this. AI only refines what you already have;
            you review and choose whether to apply it.
          </p>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Optional instructions, e.g. 'make this suitable for a lower-ability group'"
            rows={2}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          />

          {resources.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-700">Ground it in these resources (optional):</p>
              <div className="mt-1 flex flex-col gap-1">
                {resources.map((r) => (
                  <label key={r.id} className="flex items-center gap-2 text-xs text-slate-600">
                    <input
                      type="checkbox"
                      checked={selectedResourceIds.includes(r.id)}
                      onChange={() => toggleResource(r.id)}
                    />
                    {r.file_name}
                  </label>
                ))}
              </div>
            </div>
          )}

          <Button className="self-start text-sm" onClick={handleGenerate} disabled={loading}>
            {loading ? "Generating…" : "Generate suggestion"}
          </Button>

          {error && <p className="text-sm text-red-600">{error}</p>}

          {suggestion && (
            <div className="rounded-lg border border-brand-200 bg-brand-50 p-3">
              <p className="text-xs font-semibold text-brand-900">
                AI suggestion — {suggestion.sections.length} section(s), {suggestion.learning_objectives.length}{" "}
                objective(s). Nothing is saved until you apply it and hit Save.
              </p>
              <div className="mt-2 flex gap-2">
                <Button
                  className="text-xs"
                  onClick={() => {
                    onApply(suggestion);
                    setSuggestion(null);
                    setOpen(false);
                  }}
                >
                  Apply to editor
                </Button>
                <Button variant="secondary" className="text-xs" onClick={() => setSuggestion(null)}>
                  Discard
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
