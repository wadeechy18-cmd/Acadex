"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError, downloadFile } from "@/lib/api-client";
import type { HomeworkContent, LessonPlan, LessonPlanContent, LessonPlanVersion, Resource, TimelineEntry, WorksheetContent } from "@/types";

const WORKSHEET_QUESTION_SECTIONS: { key: keyof WorksheetContent; label: string }[] = [
  { key: "recall_questions", label: "Recall questions" },
  { key: "understanding_questions", label: "Understanding questions" },
  { key: "application_questions", label: "Application questions" },
  { key: "challenge_questions", label: "Challenge questions" },
];

const textAreaClass =
  "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

const LIST_SECTIONS: { key: keyof LessonPlanContent; label: string }[] = [
  { key: "learning_objectives", label: "Learning objectives" },
  { key: "success_criteria", label: "Success criteria" },
  { key: "key_vocabulary", label: "Key vocabulary" },
  { key: "resources_needed", label: "Resources needed" },
  { key: "key_questions", label: "Key questions" },
  { key: "misconceptions", label: "Common misconceptions" },
];

const TEXT_SECTIONS: { key: keyof LessonPlanContent; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "prior_knowledge", label: "Prior knowledge" },
  { key: "starter", label: "Starter" },
  { key: "teacher_explanation", label: "Teacher explanation" },
  { key: "guided_practice", label: "Guided practice" },
  { key: "independent_practice", label: "Independent practice" },
  { key: "assessment", label: "Assessment" },
  { key: "plenary", label: "Plenary" },
  { key: "homework", label: "Homework" },
  { key: "cross_curricular_links", label: "Cross-curricular links" },
];

export default function LessonPlanEditorPage() {
  const params = useParams();
  const planId = params.id as string;

  const [plan, setPlan] = useState<LessonPlan | null>(null);
  const [versions, setVersions] = useState<LessonPlanVersion[]>([]);
  const [viewingVersionId, setViewingVersionId] = useState<string | null>(null);
  const [content, setContent] = useState<LessonPlanContent | null>(null);
  const [worksheet, setWorksheet] = useState<WorksheetContent | null>(null);
  const [homeworkTask, setHomeworkTask] = useState<HomeworkContent | null>(null);
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [regeneratingSection, setRegeneratingSection] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [language, setLanguage] = useState<"en" | "bn">("en");
  const [translating, setTranslating] = useState(false);

  function loadAll() {
    setLoading(true);
    Promise.all([
      apiFetch<LessonPlan>(`/lesson-plans/${planId}`, undefined, true),
      apiFetch<LessonPlanVersion[]>(`/lesson-plans/${planId}/versions`, undefined, true),
      apiFetch<Resource[]>("/resources", undefined, true).catch(() => []),
    ])
      .then(([p, v, r]) => {
        setPlan(p);
        setVersions(v);
        setResources(r);
        setViewingVersionId(null);
        setContent(p.current_version.content);
        setWorksheet(p.current_version.worksheet);
        setHomeworkTask(p.current_version.homework_task);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load this lesson plan."))
      .finally(() => setLoading(false));
  }

  useEffect(loadAll, [planId]);

  const currentVersion = plan?.current_version ?? null;
  const displayedVersion = useMemo(
    () => (viewingVersionId ? versions.find((v) => v.id === viewingVersionId) ?? currentVersion : currentVersion),
    [viewingVersionId, versions, currentVersion]
  );
  const isViewingOldVersion = viewingVersionId !== null && viewingVersionId !== currentVersion?.id;

  function selectVersion(versionId: string) {
    const version = versions.find((v) => v.id === versionId);
    if (!version) return;
    setViewingVersionId(versionId === currentVersion?.id ? null : versionId);
    setContent(version.content);
    setWorksheet(version.worksheet);
    setHomeworkTask(version.homework_task);
    setLanguage("en");
  }

  function updateField<K extends keyof LessonPlanContent>(key: K, value: LessonPlanContent[K]) {
    setContent((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function updateListItem(key: keyof LessonPlanContent, index: number, value: string) {
    if (!content) return;
    const list = [...(content[key] as string[])];
    list[index] = value;
    updateField(key, list as never);
  }

  function addListItem(key: keyof LessonPlanContent) {
    if (!content) return;
    updateField(key, [...(content[key] as string[]), ""] as never);
  }

  function removeListItem(key: keyof LessonPlanContent, index: number) {
    if (!content) return;
    const list = [...(content[key] as string[])];
    list.splice(index, 1);
    updateField(key, list as never);
  }

  function moveListItem(key: keyof LessonPlanContent, index: number, direction: -1 | 1) {
    if (!content) return;
    const list = [...(content[key] as string[])];
    const target = index + direction;
    if (target < 0 || target >= list.length) return;
    [list[index], list[target]] = [list[target], list[index]];
    updateField(key, list as never);
  }

  function updateTimelineEntry(index: number, patch: Partial<TimelineEntry>) {
    if (!content) return;
    const timeline = content.timeline.map((entry, i) => (i === index ? { ...entry, ...patch } : entry));
    updateField("timeline", timeline);
  }

  function addTimelineEntry() {
    if (!content) return;
    updateField("timeline", [...content.timeline, { start_minute: 0, end_minute: 0, activity: "", description: "" }]);
  }

  function removeTimelineEntry(index: number) {
    if (!content) return;
    updateField(
      "timeline",
      content.timeline.filter((_, i) => i !== index)
    );
  }

  function moveTimelineEntry(index: number, direction: -1 | 1) {
    if (!content) return;
    const timeline = [...content.timeline];
    const target = index + direction;
    if (target < 0 || target >= timeline.length) return;
    [timeline[index], timeline[target]] = [timeline[target], timeline[index]];
    updateField("timeline", timeline);
  }

  function updateWorksheetField<K extends keyof WorksheetContent>(key: K, value: WorksheetContent[K]) {
    setWorksheet((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function updateWorksheetQuestion(key: keyof WorksheetContent, index: number, value: string) {
    if (!worksheet) return;
    const list = [...(worksheet[key] as string[])];
    list[index] = value;
    updateWorksheetField(key, list as never);
  }

  function addWorksheetQuestion(key: keyof WorksheetContent) {
    if (!worksheet) return;
    updateWorksheetField(key, [...(worksheet[key] as string[]), ""] as never);
  }

  function removeWorksheetQuestion(key: keyof WorksheetContent, index: number) {
    if (!worksheet) return;
    const list = [...(worksheet[key] as string[])];
    list.splice(index, 1);
    updateWorksheetField(key, list as never);
  }

  function updateHomeworkField<K extends keyof HomeworkContent>(key: K, value: HomeworkContent[K]) {
    setHomeworkTask((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function updateHomeworkTaskItem(index: number, value: string) {
    if (!homeworkTask) return;
    const tasks = [...homeworkTask.tasks];
    tasks[index] = value;
    updateHomeworkField("tasks", tasks);
  }

  function addHomeworkTask() {
    if (!homeworkTask) return;
    updateHomeworkField("tasks", [...homeworkTask.tasks, ""]);
  }

  function removeHomeworkTask(index: number) {
    if (!homeworkTask) return;
    updateHomeworkField(
      "tasks",
      homeworkTask.tasks.filter((_, i) => i !== index)
    );
  }

  async function handleSave() {
    if (!content || !currentVersion || !plan) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch(
        `/lesson-plans/${planId}/versions/${currentVersion.id}`,
        { method: "PATCH", body: JSON.stringify({ content, worksheet, homework_task: homeworkTask }) },
        true
      );
      setMessage("Saved.");
      loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveAsNewVersion() {
    if (!content) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch(
        `/lesson-plans/${planId}/versions`,
        { method: "POST", body: JSON.stringify({ content, worksheet, homework_task: homeworkTask }) },
        true
      );
      setMessage("Saved as a new version.");
      loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save a new version.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRegenerateWorksheet() {
    setRegeneratingSection("worksheet");
    setError(null);
    try {
      const version = await apiFetch<LessonPlanVersion>(`/lesson-plans/${planId}/worksheet/regenerate`, { method: "POST", body: JSON.stringify({}) }, true);
      setWorksheet(version.worksheet);
      loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't regenerate the worksheet.");
    } finally {
      setRegeneratingSection(null);
    }
  }

  async function handleRegenerateHomework() {
    setRegeneratingSection("homework");
    setError(null);
    try {
      const version = await apiFetch<LessonPlanVersion>(`/lesson-plans/${planId}/homework/regenerate`, { method: "POST", body: JSON.stringify({}) }, true);
      setHomeworkTask(version.homework_task);
      loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't regenerate the homework.");
    } finally {
      setRegeneratingSection(null);
    }
  }

  async function handleToggleLanguage(target: "en" | "bn") {
    if (target === "en" || !displayedVersion) {
      setLanguage(target);
      return;
    }
    setLanguage("bn");
    if (displayedVersion.translation_bn) return;
    setTranslating(true);
    setError(null);
    try {
      await apiFetch<LessonPlanVersion>(`/lesson-plans/${planId}/versions/${displayedVersion.id}/translate`, { method: "POST" }, true);
      loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't translate this lesson.");
      setLanguage("en");
    } finally {
      setTranslating(false);
    }
  }

  async function handleRestore(versionId: string) {
    await apiFetch(`/lesson-plans/${planId}/versions/${versionId}/restore`, { method: "POST" }, true);
    loadAll();
  }

  async function handleRegenerate(sectionKey: string) {
    setRegeneratingSection(sectionKey);
    setError(null);
    try {
      const version = await apiFetch<LessonPlanVersion>(
        `/lesson-plans/${planId}/sections/${sectionKey}/regenerate`,
        { method: "POST", body: JSON.stringify({}) },
        true
      );
      setContent(version.content);
      loadAll();
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setError("AI generation isn't configured on this server.");
      } else {
        setError(err instanceof ApiError ? err.message : "Couldn't regenerate that section.");
      }
    } finally {
      setRegeneratingSection(null);
    }
  }

  if (loading) return <main className="p-8 text-sm text-muted-foreground">Loading…</main>;
  if (error && !plan) return <main className="p-8 text-sm text-destructive">{error}</main>;
  if (!plan || !content) return null;

  const readOnly = isViewingOldVersion;

  return (
    <main className="mx-auto flex max-w-5xl gap-8 p-8 print:block">
      <div className="flex-1">
        <div className="flex items-center justify-between gap-4">
          <Input
            className="text-xl font-bold"
            value={content.title}
            onChange={(e) => updateField("title", e.target.value)}
            disabled={readOnly}
          />
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {plan.subject_name} · {plan.year_group_name} · {plan.duration_minutes} min · {plan.ability_level}
          {plan.scheduled_date && ` · ${new Date(plan.scheduled_date).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}`}
        </p>

        <div className="mt-3 flex gap-2 print:hidden">
          <Button size="sm" variant={language === "en" ? "default" : "outline"} onClick={() => handleToggleLanguage("en")}>
            English
          </Button>
          <Button size="sm" variant={language === "bn" ? "default" : "outline"} disabled={translating} onClick={() => handleToggleLanguage("bn")}>
            {translating ? "Translating…" : "Translate to বাংলা"}
          </Button>
        </div>

        {displayedVersion?.safeguarding_flagged && (
          <div className="mt-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
            {displayedVersion.safeguarding_notes}
          </div>
        )}
        {readOnly && (
          <div className="mt-4 rounded-md border bg-muted/40 p-3 text-sm">
            Viewing version {displayedVersion?.version_number} (read-only).{" "}
            <button className="underline" onClick={() => selectVersion(currentVersion!.id)}>
              Back to current
            </button>
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2 print:hidden">
          <Button onClick={handleSave} disabled={saving || readOnly}>
            Save
          </Button>
          <Button variant="outline" onClick={handleSaveAsNewVersion} disabled={saving || readOnly}>
            Save as new version
          </Button>
          <Button variant="outline" onClick={() => downloadFile(`/lesson-plans/${planId}/versions/${displayedVersion!.id}/export.pdf`)}>
            Export PDF
          </Button>
          <Button variant="outline" onClick={() => downloadFile(`/lesson-plans/${planId}/versions/${displayedVersion!.id}/export.docx`)}>
            Export DOCX
          </Button>
          <Button variant="outline" onClick={() => window.print()}>
            Print
          </Button>
        </div>
        {message && <p className="mt-2 text-sm text-muted-foreground">{message}</p>}
        {error && <p className="mt-2 text-sm text-destructive">{error}</p>}

        <div className="mt-8 flex flex-col gap-8">
          {TEXT_SECTIONS.map(({ key, label }) => (
            <section key={key}>
              <div className="flex items-center justify-between">
                <Label>{label}</Label>
                <Button
                  variant="outline"
                  size="sm"
                  className="print:hidden"
                  disabled={readOnly || regeneratingSection === key}
                  onClick={() => handleRegenerate(key)}
                >
                  {regeneratingSection === key ? "Regenerating…" : "Regenerate"}
                </Button>
              </div>
              <textarea
                className={`${textAreaClass} mt-2 h-24`}
                value={content[key] as string}
                onChange={(e) => updateField(key, e.target.value as never)}
                disabled={readOnly}
              />
            </section>
          ))}

          {LIST_SECTIONS.map(({ key, label }) => (
            <section key={key}>
              <div className="flex items-center justify-between">
                <Label>{label}</Label>
                <Button
                  variant="outline"
                  size="sm"
                  className="print:hidden"
                  disabled={readOnly || regeneratingSection === key}
                  onClick={() => handleRegenerate(key)}
                >
                  {regeneratingSection === key ? "Regenerating…" : "Regenerate"}
                </Button>
              </div>
              <div className="mt-2 flex flex-col gap-2">
                {(content[key] as string[]).map((item, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input value={item} onChange={(e) => updateListItem(key, i, e.target.value)} disabled={readOnly} />
                    {!readOnly && (
                      <div className="flex shrink-0 gap-1 print:hidden">
                        <Button variant="outline" size="sm" onClick={() => moveListItem(key, i, -1)}>
                          ↑
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => moveListItem(key, i, 1)}>
                          ↓
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => removeListItem(key, i)}>
                          Remove
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
                {!readOnly && (
                  <Button variant="outline" size="sm" className="self-start print:hidden" onClick={() => addListItem(key)}>
                    Add item
                  </Button>
                )}
              </div>
            </section>
          ))}

          <section>
            <div className="flex items-center justify-between">
              <Label>Differentiation</Label>
              <Button
                variant="outline"
                size="sm"
                className="print:hidden"
                disabled={readOnly || regeneratingSection === "differentiation"}
                onClick={() => handleRegenerate("differentiation")}
              >
                {regeneratingSection === "differentiation" ? "Regenerating…" : "Regenerate"}
              </Button>
            </div>
            {(["support", "core", "greater_depth"] as const).map((tier) => (
              <div key={tier} className="mt-2">
                <Label className="text-xs capitalize text-muted-foreground">{tier.replace("_", " ")}</Label>
                <textarea
                  className={`${textAreaClass} h-16`}
                  value={content.differentiation[tier]}
                  onChange={(e) => updateField("differentiation", { ...content.differentiation, [tier]: e.target.value })}
                  disabled={readOnly}
                />
              </div>
            ))}
          </section>

          <section>
            <div className="flex items-center justify-between">
              <Label>Timeline</Label>
              <Button
                variant="outline"
                size="sm"
                className="print:hidden"
                disabled={readOnly || regeneratingSection === "timeline"}
                onClick={() => handleRegenerate("timeline")}
              >
                {regeneratingSection === "timeline" ? "Regenerating…" : "Regenerate"}
              </Button>
            </div>
            <div className="mt-2 flex flex-col gap-2">
              {content.timeline.map((entry, i) => (
                <div key={i} className="rounded-md border p-3">
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      className="w-20"
                      value={entry.start_minute}
                      onChange={(e) => updateTimelineEntry(i, { start_minute: Number(e.target.value) })}
                      disabled={readOnly}
                    />
                    <Input
                      type="number"
                      className="w-20"
                      value={entry.end_minute}
                      onChange={(e) => updateTimelineEntry(i, { end_minute: Number(e.target.value) })}
                      disabled={readOnly}
                    />
                    <Input
                      placeholder="Activity"
                      value={entry.activity}
                      onChange={(e) => updateTimelineEntry(i, { activity: e.target.value })}
                      disabled={readOnly}
                    />
                  </div>
                  <textarea
                    className={`${textAreaClass} mt-2 h-16`}
                    placeholder="Description"
                    value={entry.description}
                    onChange={(e) => updateTimelineEntry(i, { description: e.target.value })}
                    disabled={readOnly}
                  />
                  {!readOnly && (
                    <div className="mt-2 flex gap-1 print:hidden">
                      <Button variant="outline" size="sm" onClick={() => moveTimelineEntry(i, -1)}>
                        ↑
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => moveTimelineEntry(i, 1)}>
                        ↓
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => removeTimelineEntry(i)}>
                        Remove
                      </Button>
                    </div>
                  )}
                </div>
              ))}
              {!readOnly && (
                <Button variant="outline" size="sm" className="self-start print:hidden" onClick={addTimelineEntry}>
                  Add step
                </Button>
              )}
            </div>
          </section>

          {worksheet && (
            <section className="rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Worksheet</h2>
                <div className="flex gap-2 print:hidden">
                  <Button variant="outline" size="sm" disabled={readOnly || regeneratingSection === "worksheet"} onClick={handleRegenerateWorksheet}>
                    {regeneratingSection === "worksheet" ? "Regenerating…" : "Regenerate"}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => downloadFile(`/lesson-plans/${planId}/versions/${displayedVersion!.id}/worksheet/export.pdf`)}>
                    Export PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => downloadFile(`/lesson-plans/${planId}/versions/${displayedVersion!.id}/worksheet/export.docx`)}>
                    Export DOCX
                  </Button>
                </div>
              </div>
              <Input className="mt-3 font-medium" value={worksheet.title} onChange={(e) => updateWorksheetField("title", e.target.value)} disabled={readOnly} />
              <textarea
                className={`${textAreaClass} mt-2 h-16`}
                value={worksheet.instructions}
                onChange={(e) => updateWorksheetField("instructions", e.target.value)}
                disabled={readOnly}
              />
              {WORKSHEET_QUESTION_SECTIONS.map(({ key, label }) => (
                <div key={key} className="mt-4">
                  <Label>{label}</Label>
                  <div className="mt-2 flex flex-col gap-2">
                    {(worksheet[key] as string[]).map((q, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <Input value={q} onChange={(e) => updateWorksheetQuestion(key, i, e.target.value)} disabled={readOnly} />
                        {!readOnly && (
                          <Button variant="outline" size="sm" className="print:hidden" onClick={() => removeWorksheetQuestion(key, i)}>
                            Remove
                          </Button>
                        )}
                      </div>
                    ))}
                    {!readOnly && (
                      <Button variant="outline" size="sm" className="self-start print:hidden" onClick={() => addWorksheetQuestion(key)}>
                        Add question
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </section>
          )}

          {homeworkTask && (
            <section className="rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Homework</h2>
                <div className="flex gap-2 print:hidden">
                  <Button variant="outline" size="sm" disabled={readOnly || regeneratingSection === "homework"} onClick={handleRegenerateHomework}>
                    {regeneratingSection === "homework" ? "Regenerating…" : "Regenerate"}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => downloadFile(`/lesson-plans/${planId}/versions/${displayedVersion!.id}/homework/export.pdf`)}>
                    Export PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => downloadFile(`/lesson-plans/${planId}/versions/${displayedVersion!.id}/homework/export.docx`)}>
                    Export DOCX
                  </Button>
                </div>
              </div>
              <Input className="mt-3 font-medium" value={homeworkTask.title} onChange={(e) => updateHomeworkField("title", e.target.value)} disabled={readOnly} />
              <textarea
                className={`${textAreaClass} mt-2 h-16`}
                value={homeworkTask.instructions}
                onChange={(e) => updateHomeworkField("instructions", e.target.value)}
                disabled={readOnly}
              />
              <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                <Label>Estimated minutes</Label>
                <Input
                  type="number"
                  className="w-20"
                  value={homeworkTask.estimated_minutes}
                  onChange={(e) => updateHomeworkField("estimated_minutes", Number(e.target.value))}
                  disabled={readOnly}
                />
              </div>
              <div className="mt-4 flex flex-col gap-2">
                {homeworkTask.tasks.map((task, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input value={task} onChange={(e) => updateHomeworkTaskItem(i, e.target.value)} disabled={readOnly} />
                    {!readOnly && (
                      <Button variant="outline" size="sm" className="print:hidden" onClick={() => removeHomeworkTask(i)}>
                        Remove
                      </Button>
                    )}
                  </div>
                ))}
                {!readOnly && (
                  <Button variant="outline" size="sm" className="self-start print:hidden" onClick={addHomeworkTask}>
                    Add task
                  </Button>
                )}
              </div>
            </section>
          )}

          {displayedVersion && displayedVersion.resource_ids.length > 0 && (
            <section className="rounded-lg border p-4 print:hidden">
              <h2 className="text-lg font-semibold">Resources used</h2>
              <p className="mt-1 text-sm text-muted-foreground">Automatically matched from your resource library for this lesson.</p>
              <ul className="mt-2 list-disc pl-5 text-sm">
                {displayedVersion.resource_ids.map((id) => (
                  <li key={id}>{resources.find((r) => r.id === id)?.display_name ?? "Untitled resource"}</li>
                ))}
              </ul>
            </section>
          )}

          {language === "bn" && (
            <section className="rounded-lg border p-4">
              <h2 className="text-lg font-semibold">বাংলা অনুবাদ (Bangla translation)</h2>
              {translating && <p className="mt-2 text-sm text-muted-foreground">Translating…</p>}
              {!translating && displayedVersion?.translation_bn && (
                <div className="mt-2 flex flex-col gap-4 text-sm">
                  <div>
                    <p className="font-medium">{displayedVersion.translation_bn.lesson.title}</p>
                    <p className="mt-1 text-muted-foreground">{displayedVersion.translation_bn.lesson.overview}</p>
                  </div>
                  <div>
                    <Label>Learning objectives</Label>
                    <ul className="mt-1 list-disc pl-5">
                      {displayedVersion.translation_bn.lesson.learning_objectives.map((o, i) => (
                        <li key={i}>{o}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <Label>Teacher explanation</Label>
                    <p className="mt-1">{displayedVersion.translation_bn.lesson.teacher_explanation}</p>
                  </div>
                  <div>
                    <Label>Differentiation</Label>
                    <p className="mt-1">সহায়তা (Support): {displayedVersion.translation_bn.lesson.differentiation.support}</p>
                    <p className="mt-1">মূল (Core): {displayedVersion.translation_bn.lesson.differentiation.core}</p>
                    <p className="mt-1">গভীরতা (Greater depth): {displayedVersion.translation_bn.lesson.differentiation.greater_depth}</p>
                  </div>
                  <div>
                    <Label>Homework note</Label>
                    <p className="mt-1">{displayedVersion.translation_bn.lesson.homework}</p>
                  </div>
                  {displayedVersion.translation_bn.worksheet && (
                    <div>
                      <Label>{displayedVersion.translation_bn.worksheet.title}</Label>
                      <p className="mt-1 text-muted-foreground">{displayedVersion.translation_bn.worksheet.instructions}</p>
                    </div>
                  )}
                  {displayedVersion.translation_bn.homework && (
                    <div>
                      <Label>{displayedVersion.translation_bn.homework.title}</Label>
                      <ul className="mt-1 list-disc pl-5">
                        {displayedVersion.translation_bn.homework.tasks.map((t, i) => (
                          <li key={i}>{t}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {displayedVersion.safeguarding_flagged && (
                    <div>
                      <Label>Safeguarding / নিরাপত্তা</Label>
                      <p className="mt-1 text-destructive">{displayedVersion.safeguarding_notes}</p>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}
        </div>
      </div>

      <aside className="w-64 shrink-0 print:hidden">
        <h2 className="font-semibold">Versions</h2>
        <div className="mt-2 flex flex-col gap-1">
          {versions.map((v) => (
            <div key={v.id} className={`rounded-md border p-2 text-sm ${v.id === (viewingVersionId ?? currentVersion?.id) ? "bg-accent" : ""}`}>
              <button className="text-left font-medium hover:underline" onClick={() => selectVersion(v.id)}>
                Version {v.version_number}
              </button>
              <p className="text-xs text-muted-foreground">{v.generation_kind.replace("_", " ")}</p>
              {v.id !== currentVersion?.id && (
                <Button variant="outline" size="sm" className="mt-1" onClick={() => handleRestore(v.id)}>
                  Restore
                </Button>
              )}
            </div>
          ))}
        </div>
      </aside>
    </main>
  );
}
