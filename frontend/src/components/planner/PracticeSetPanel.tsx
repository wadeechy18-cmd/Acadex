"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError, downloadFile } from "@/lib/api-client";
import type { AnswerKey, Homework, PracticeItem, PracticeSetContent, Resource, Worksheet } from "@/types";

type PracticeSet = Worksheet | Homework;

interface Props {
  lessonPlanId: string;
  kind: "worksheet" | "homework";
  resources: Resource[];
  readOnly: boolean;
}

function newItemId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `item-${Date.now()}-${Math.random()}`;
}

const EMPTY_CONTENT: PracticeSetContent = { instructions: "", items: [] };

function isHomework(kind: "worksheet" | "homework", item: PracticeSet): item is Homework {
  return kind === "homework";
}

export function PracticeSetPanel({ lessonPlanId, kind, resources, readOnly }: Props) {
  const label = kind === "worksheet" ? "Worksheets" : "Homework";
  const basePath = kind === "worksheet" ? "worksheets" : "homework";

  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<PracticeSet[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [answerKeys, setAnswerKeys] = useState<Record<string, AnswerKey>>({});
  const [exportError, setExportError] = useState<string | null>(null);

  const [aiOpen, setAiOpen] = useState(false);
  const [aiInstructions, setAiInstructions] = useState("");
  const [aiItemCount, setAiItemCount] = useState(8);
  const [aiResourceIds, setAiResourceIds] = useState<string[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const rows = await apiFetch<PracticeSet[]>(`/lesson-plans/${lessonPlanId}/${basePath}`, undefined, true);
      setItems(rows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Couldn't load ${label.toLowerCase()}.`);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(content: PracticeSetContent = EMPTY_CONTENT) {
    const payload: Record<string, unknown> = { title: `New ${kind}`, content };
    if (kind === "homework") payload.due_date = null;
    const created = await apiFetch<PracticeSet>(`/lesson-plans/${lessonPlanId}/${basePath}`, { method: "POST", body: JSON.stringify(payload) }, true);
    setItems((prev) => [created, ...prev]);
    setExpandedId(created.id);
  }

  async function handleUpdate(id: string, updates: Record<string, unknown>) {
    const updated = await apiFetch<PracticeSet>(`/${basePath}/${id}`, { method: "PATCH", body: JSON.stringify(updates) }, true);
    setItems((prev) => prev.map((i) => (i.id === id ? updated : i)));
    setAnswerKeys((prev) => {
      const next = { ...prev };
      delete next[id]; // content changed -- force a fresh derived key on next view
      return next;
    });
  }

  async function handleDelete(id: string) {
    await apiFetch(`/${basePath}/${id}`, { method: "DELETE" }, true);
    setItems((prev) => prev.filter((i) => i.id !== id));
    if (expandedId === id) setExpandedId(null);
  }

  async function handleExport(itemId: string, format: "pdf" | "docx", includeAnswers: boolean) {
    setExportError(null);
    try {
      await downloadFile(`/${basePath}/${itemId}/export?format=${format}&include_answers=${includeAnswers}`);
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : `Couldn't export this ${kind}.`);
    }
  }

  async function toggleAnswerKey(id: string) {
    if (answerKeys[id]) {
      setAnswerKeys((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      return;
    }
    const key = await apiFetch<AnswerKey>(`/${basePath}/${id}/answer-key`, undefined, true);
    setAnswerKeys((prev) => ({ ...prev, [id]: key }));
  }

  function toggleAiResource(id: string) {
    setAiResourceIds((prev) => (prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]));
  }

  async function handleAiGenerate() {
    setAiError(null);
    setAiLoading(true);
    try {
      const content = await apiFetch<PracticeSetContent>(
        `/lesson-plans/${lessonPlanId}/${basePath}/ai-generate`,
        {
          method: "POST",
          body: JSON.stringify({
            instructions: aiInstructions || undefined,
            item_count: aiItemCount,
            resource_ids: aiResourceIds,
          }),
        },
        true
      );
      await handleCreate(content);
      setAiOpen(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setAiError("AI features aren't configured for this deployment yet.");
      } else {
        setAiError(err instanceof ApiError ? err.message : "Something went wrong.");
      }
    } finally {
      setAiLoading(false);
    }
  }

  function updateContentField(item: PracticeSet, content: PracticeSetContent) {
    setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, content } : i)));
  }

  function addItem(item: PracticeSet) {
    updateContentField(item, {
      ...item.content,
      items: [...item.content.items, { id: newItemId(), group: "Core", prompt: "", marks: 1, answer: "" }],
    });
  }

  function updateItem(item: PracticeSet, index: number, patch: Partial<PracticeItem>) {
    const nextItems = [...item.content.items];
    nextItems[index] = { ...nextItems[index], ...patch };
    updateContentField(item, { ...item.content, items: nextItems });
  }

  function removeItem(item: PracticeSet, index: number) {
    updateContentField(item, { ...item.content, items: item.content.items.filter((_, i) => i !== index) });
  }

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <button type="button" onClick={() => setOpen((v) => !v)} className="text-sm font-semibold text-slate-900">
        {kind === "worksheet" ? "📝" : "🏠"} {label} {open ? "▲" : "▼"}
      </button>

      {open && (
        <div className="mt-3 flex flex-col gap-4">
          {loading && <p className="text-sm text-slate-500">Loading…</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {exportError && <p className="text-sm text-red-600">{exportError}</p>}

          {!readOnly && (
            <div className="flex flex-wrap gap-2">
              <Button className="text-sm" onClick={() => handleCreate()}>
                + New {kind}
              </Button>
              <Button variant="secondary" className="text-sm" onClick={() => setAiOpen((v) => !v)}>
                ✨ AI generate {aiOpen ? "▲" : "▼"}
              </Button>
            </div>
          )}

          {aiOpen && !readOnly && (
            <div className="rounded-lg border border-slate-200 p-3">
              <p className="text-xs text-slate-500">
                Optional -- generates a draft {kind} linked to this lesson, which you review, edit, and save.
              </p>
              <textarea
                value={aiInstructions}
                onChange={(e) => setAiInstructions(e.target.value)}
                placeholder="Optional instructions, e.g. 'focus on fractions'"
                rows={2}
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              />
              <label className="mt-2 flex items-center gap-2 text-xs text-slate-600">
                Number of items
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={aiItemCount}
                  onChange={(e) => setAiItemCount(Number(e.target.value))}
                  className="w-16 rounded border border-slate-300 px-2 py-1 text-xs"
                />
              </label>
              {resources.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-slate-700">Ground it in these resources (optional):</p>
                  <div className="mt-1 flex flex-col gap-1">
                    {resources.map((r) => (
                      <label key={r.id} className="flex items-center gap-2 text-xs text-slate-600">
                        <input type="checkbox" checked={aiResourceIds.includes(r.id)} onChange={() => toggleAiResource(r.id)} />
                        {r.file_name}
                      </label>
                    ))}
                  </div>
                </div>
              )}
              <Button className="mt-2 text-xs" onClick={handleAiGenerate} disabled={aiLoading}>
                {aiLoading ? "Generating…" : "Generate"}
              </Button>
              {aiError && <p className="mt-2 text-sm text-red-600">{aiError}</p>}
            </div>
          )}

          {items.length === 0 && !loading && <p className="text-sm text-slate-400">No {label.toLowerCase()} yet.</p>}

          <div className="flex flex-col gap-3">
            {items.map((item) => {
              const expanded = expandedId === item.id;
              const answerKey = answerKeys[item.id];
              return (
                <div key={item.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <button type="button" onClick={() => setExpandedId(expanded ? null : item.id)} className="text-sm font-medium text-slate-900">
                      {item.title}
                    </button>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span>
                        {item.total_marks} marks · ~{item.estimated_minutes} min
                      </span>
                      {isHomework(kind, item) && item.due_date && <span>due {item.due_date}</span>}
                      <button type="button" onClick={() => toggleAnswerKey(item.id)} className="font-medium text-brand-700 hover:underline">
                        {answerKey ? "Hide" : "Show"} answer key
                      </button>
                      {!readOnly && (
                        <button type="button" onClick={() => handleDelete(item.id)} className="font-medium text-red-600 hover:underline">
                          Delete
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="mt-1 flex items-center gap-3 text-xs text-slate-400">
                    <span>Export:</span>
                    <button type="button" onClick={() => handleExport(item.id, "pdf", false)} className="font-medium text-brand-700 hover:underline">
                      PDF
                    </button>
                    <button type="button" onClick={() => handleExport(item.id, "pdf", true)} className="font-medium text-brand-700 hover:underline">
                      PDF (with answers)
                    </button>
                    <button type="button" onClick={() => handleExport(item.id, "docx", false)} className="font-medium text-brand-700 hover:underline">
                      DOCX
                    </button>
                    <button type="button" onClick={() => handleExport(item.id, "docx", true)} className="font-medium text-brand-700 hover:underline">
                      DOCX (with answers)
                    </button>
                  </div>

                  {answerKey && (
                    <div className="mt-2 rounded bg-slate-50 p-2 text-xs text-slate-700">
                      {answerKey.entries.map((e) => (
                        <div key={e.id} className="border-b border-slate-100 py-1 last:border-0">
                          <span className="font-medium">{e.prompt}</span> ({e.marks} mark{e.marks === 1 ? "" : "s"}) — {e.answer || "no answer given"}
                        </div>
                      ))}
                    </div>
                  )}

                  {expanded && (
                    <div className="mt-3 flex flex-col gap-3">
                      <input
                        value={item.title}
                        disabled={readOnly}
                        onChange={(e) => setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, title: e.target.value } : i)))}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-60"
                      />
                      {isHomework(kind, item) && (
                        <label className="flex items-center gap-2 text-xs text-slate-600">
                          Due date
                          <input
                            type="date"
                            disabled={readOnly}
                            value={item.due_date ?? ""}
                            onChange={(e) =>
                              setItems((prev) =>
                                prev.map((i) => (i.id === item.id ? ({ ...i, due_date: e.target.value || null } as PracticeSet) : i))
                              )
                            }
                            className="rounded border border-slate-300 px-2 py-1 text-xs disabled:opacity-60"
                          />
                        </label>
                      )}
                      <textarea
                        value={item.content.instructions ?? ""}
                        disabled={readOnly}
                        onChange={(e) => updateContentField(item, { ...item.content, instructions: e.target.value })}
                        placeholder="Instructions for the student"
                        rows={2}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-60"
                      />

                      <div className="flex flex-col gap-2">
                        {item.content.items.map((practiceItem, i) => (
                          <div key={practiceItem.id} className="grid grid-cols-12 gap-2">
                            <input
                              value={practiceItem.group}
                              disabled={readOnly}
                              onChange={(e) => updateItem(item, i, { group: e.target.value })}
                              placeholder="Group"
                              className="col-span-2 rounded border border-slate-300 px-2 py-1 text-xs disabled:opacity-60"
                            />
                            <input
                              value={practiceItem.prompt}
                              disabled={readOnly}
                              onChange={(e) => updateItem(item, i, { prompt: e.target.value })}
                              placeholder="Prompt"
                              className="col-span-4 rounded border border-slate-300 px-2 py-1 text-xs disabled:opacity-60"
                            />
                            <input
                              type="number"
                              min={0}
                              value={practiceItem.marks}
                              disabled={readOnly}
                              onChange={(e) => updateItem(item, i, { marks: Number(e.target.value) })}
                              placeholder="Marks"
                              className="col-span-1 rounded border border-slate-300 px-2 py-1 text-xs disabled:opacity-60"
                            />
                            <input
                              value={practiceItem.answer}
                              disabled={readOnly}
                              onChange={(e) => updateItem(item, i, { answer: e.target.value })}
                              placeholder="Answer"
                              className="col-span-4 rounded border border-slate-300 px-2 py-1 text-xs disabled:opacity-60"
                            />
                            {!readOnly && (
                              <button type="button" onClick={() => removeItem(item, i)} className="col-span-1 text-xs text-red-600 hover:underline">
                                ✕
                              </button>
                            )}
                          </div>
                        ))}
                      </div>

                      {!readOnly && (
                        <div className="flex gap-2">
                          <button type="button" onClick={() => addItem(item)} className="text-xs font-medium text-brand-700 hover:underline">
                            + Add item
                          </button>
                          <Button
                            className="text-xs"
                            onClick={() => {
                              const updates: Record<string, unknown> = { title: item.title, content: item.content };
                              if (isHomework(kind, item)) updates.due_date = item.due_date;
                              handleUpdate(item.id, updates);
                            }}
                          >
                            Save
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
