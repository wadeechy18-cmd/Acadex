"use client";

import { DndContext, PointerSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, arrayMove, verticalListSortingStrategy } from "@dnd-kit/sortable";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { AIEnhancePanel } from "@/components/planner/AIEnhancePanel";
import { PracticeSetPanel } from "@/components/planner/PracticeSetPanel";
import { QualityPanel } from "@/components/planner/QualityPanel";
import { SortableSection } from "@/components/planner/SortableSection";
import { StringListEditor } from "@/components/planner/StringListEditor";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type {
  LessonPlanContent,
  LessonPlanDetail,
  LessonPlanQualityReport,
  LessonPlanVersionSummary,
  LessonSection,
  Resource,
  TimingSuggestion,
} from "@/types";

function newSectionId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `s-${Date.now()}-${Math.random()}`;
}

const EMPTY_CONTENT: LessonPlanContent = {
  learning_objectives: [],
  success_criteria: [],
  prior_knowledge: [],
  key_vocabulary: [],
  sections: [],
  differentiation: null,
  assessment_for_learning: [],
  misconceptions: [],
  teacher_notes: null,
  safeguarding_note: null,
};

export default function LessonPlanEditorPage() {
  const { orgId, classId, planId } = useParams<{ orgId: string; classId: string; planId: string }>();
  const router = useRouter();
  const { user, loading } = useAuth();

  const [plan, setPlan] = useState<LessonPlanDetail | null>(null);
  const [content, setContent] = useState<LessonPlanContent>(EMPTY_CONTENT);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const [versions, setVersions] = useState<LessonPlanVersionSummary[]>([]);
  const [showVersions, setShowVersions] = useState(false);
  const [qualityReport, setQualityReport] = useState<LessonPlanQualityReport | null>(null);
  const [resources, setResources] = useState<Resource[]>([]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  useEffect(() => {
    if (!loading && (!user || user.role !== "teacher")) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user || user.role !== "teacher" || !planId) return;
    apiFetch<LessonPlanDetail>(`/lesson-plans/${planId}`, undefined, true)
      .then((detail) => {
        setPlan(detail);
        setContent(detail.content);
        return checkQuality(detail, detail.content);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load this lesson plan."))
      .finally(() => setDataLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, planId]);

  useEffect(() => {
    if (!user || user.role !== "teacher" || !orgId) return;
    apiFetch<Resource[]>(`/organizations/${orgId}/resources`, undefined, true)
      .then(setResources)
      .catch(() => {
        // Non-critical -- the AI panel just shows no resource checklist.
      });
  }, [user, orgId]);

  const isOwner = !!(plan && user && plan.teacher_user_id === user.id);

  async function checkQuality(currentPlan: LessonPlanDetail, currentContent: LessonPlanContent) {
    try {
      const report = await apiFetch<LessonPlanQualityReport>(
        `/lesson-plans/${planId}/quality-check`,
        {
          method: "POST",
          body: JSON.stringify({
            title: currentPlan.title,
            topic: currentPlan.topic,
            duration_minutes: currentPlan.duration_minutes,
            template_type: currentPlan.template_type,
            content: currentContent,
          }),
        },
        true
      );
      setQualityReport(report);
    } catch {
      // Non-critical -- the editor still works without the quality panel.
    }
  }

  function applySuggestion(suggestion: TimingSuggestion) {
    let nextSections = content.sections;
    if (suggestion.action === "extend_section" && suggestion.section_id) {
      nextSections = content.sections.map((s) =>
        s.id === suggestion.section_id
          ? { ...s, duration_minutes: Math.max(0, s.duration_minutes + (suggestion.extend_by_minutes ?? 0)) }
          : s
      );
    } else if (suggestion.action === "add_section" && suggestion.new_section) {
      nextSections = [...content.sections, suggestion.new_section];
    }
    const nextContent = { ...content, sections: nextSections };
    setContent(nextContent);
    if (plan) checkQuality(plan, nextContent);
  }

  function updateSection(index: number, section: LessonSection) {
    const sections = [...content.sections];
    sections[index] = section;
    setContent({ ...content, sections });
  }

  function addSection() {
    setContent({
      ...content,
      sections: [...content.sections, { id: newSectionId(), type: "activity", title: "New section", duration_minutes: 5, body: [] }],
    });
  }

  function removeSection(index: number) {
    setContent({ ...content, sections: content.sections.filter((_, i) => i !== index) });
  }

  function duplicateSection(index: number) {
    const source = content.sections[index];
    const copy: LessonSection = { ...source, id: newSectionId(), title: `${source.title} (Copy)` };
    const sections = [...content.sections];
    sections.splice(index + 1, 0, copy);
    setContent({ ...content, sections });
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setContent((prev) => {
      const oldIndex = prev.sections.findIndex((s) => s.id === active.id);
      const newIndex = prev.sections.findIndex((s) => s.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return prev;
      return { ...prev, sections: arrayMove(prev.sections, oldIndex, newIndex) };
    });
  }

  async function handleSave() {
    setSaving(true);
    setSaveMessage(null);
    try {
      await apiFetch(`/lesson-plans/${planId}/content`, { method: "PUT", body: JSON.stringify({ content }) }, true);
      const refreshed = await apiFetch<LessonPlanDetail>(`/lesson-plans/${planId}`, undefined, true);
      setPlan(refreshed);
      setSaveMessage(`Saved as version ${refreshed.latest_version_number}.`);
      checkQuality(refreshed, content);
    } catch (err) {
      setSaveMessage(err instanceof ApiError ? err.message : "Couldn't save.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDuplicatePlan() {
    const copy = await apiFetch<{ id: string }>(`/lesson-plans/${planId}/duplicate`, { method: "POST" }, true);
    router.push(`/planner/${orgId}/classes/${classId}/lesson-plans/${copy.id}`);
  }

  async function loadVersions() {
    const rows = await apiFetch<LessonPlanVersionSummary[]>(`/lesson-plans/${planId}/versions`, undefined, true);
    setVersions(rows);
    setShowVersions(true);
  }

  async function handleRestore(versionId: string) {
    await apiFetch(`/lesson-plans/${planId}/versions/${versionId}/restore`, { method: "POST" }, true);
    const refreshed = await apiFetch<LessonPlanDetail>(`/lesson-plans/${planId}`, undefined, true);
    setPlan(refreshed);
    setContent(refreshed.content);
    checkQuality(refreshed, refreshed.content);
    loadVersions();
  }

  if (loading || !user || dataLoading) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  if (error || !plan) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-red-600">{error ?? "Lesson plan not found."}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href={`/planner/${orgId}/classes/${classId}/lesson-plans`} className="text-sm font-medium text-brand-700 hover:underline">
        ← Lesson plans
      </Link>

      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{plan.title}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {plan.topic} · {plan.template_type.replace("_", " ")} · v{plan.latest_version_number} ·{" "}
            <span className={plan.status === "published" ? "text-green-700" : "text-amber-700"}>{plan.status}</span>
            {!isOwner && " · view only"}
          </p>
        </div>
        {isOwner && (
          <div className="flex gap-2">
            <Button variant="secondary" className="text-sm" onClick={() => plan && checkQuality(plan, content)}>
              Check timing
            </Button>
            <Button variant="secondary" className="text-sm" onClick={loadVersions}>
              History
            </Button>
            <Button variant="secondary" className="text-sm" onClick={handleDuplicatePlan}>
              Duplicate
            </Button>
            <Button className="text-sm" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        )}
      </div>

      {saveMessage && <p className="mt-2 text-sm text-slate-600">{saveMessage}</p>}

      {qualityReport && (
        <div className="mt-4">
          <QualityPanel report={qualityReport} onApplySuggestion={applySuggestion} readOnly={!isOwner} />
        </div>
      )}

      {isOwner && (
        <div className="mt-4">
          <AIEnhancePanel
            lessonPlanId={planId}
            resources={resources}
            onApply={(suggested) => {
              setContent(suggested);
              if (plan) checkQuality(plan, suggested);
            }}
          />
        </div>
      )}

      <div className="mt-4 flex flex-col gap-4">
        <PracticeSetPanel lessonPlanId={planId} kind="worksheet" resources={resources} readOnly={!isOwner} />
        <PracticeSetPanel lessonPlanId={planId} kind="homework" resources={resources} readOnly={!isOwner} />
      </div>

      {showVersions && (
        <div className="mt-4 rounded-xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Version history</h2>
            <button onClick={() => setShowVersions(false)} className="text-xs text-slate-400 hover:text-slate-600">
              Close
            </button>
          </div>
          <div className="mt-2 flex flex-col gap-1">
            {versions.map((v) => (
              <div key={v.id} className="flex items-center justify-between text-sm">
                <span>
                  v{v.version_number} — {new Date(v.created_at).toLocaleString()}
                </span>
                {isOwner && v.version_number !== plan.latest_version_number && (
                  <button onClick={() => handleRestore(v.id)} className="text-xs font-medium text-brand-700 hover:underline">
                    Restore
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <fieldset disabled={!isOwner} className="mt-8 flex flex-col gap-8 disabled:opacity-70">
        <StringListEditor
          label="Learning objectives"
          items={content.learning_objectives}
          onChange={(learning_objectives) => setContent({ ...content, learning_objectives })}
          placeholder="Students will be able to..."
        />
        <StringListEditor
          label="Success criteria"
          items={content.success_criteria}
          onChange={(success_criteria) => setContent({ ...content, success_criteria })}
        />
        <StringListEditor
          label="Key vocabulary"
          items={content.key_vocabulary}
          onChange={(key_vocabulary) => setContent({ ...content, key_vocabulary })}
        />

        <div>
          <h2 className="text-lg font-semibold text-slate-900">Lesson sections</h2>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={content.sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
              <div className="mt-3 flex flex-col gap-3">
                {content.sections.map((section, i) => (
                  <SortableSection
                    key={section.id}
                    section={section}
                    onChange={(s) => updateSection(i, s)}
                    onDelete={() => removeSection(i)}
                    onDuplicate={() => duplicateSection(i)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
          {isOwner && (
            <button type="button" onClick={addSection} className="mt-3 text-sm font-medium text-brand-700 hover:underline">
              + Add Section
            </button>
          )}
        </div>

        <StringListEditor
          label="Assessment for learning"
          items={content.assessment_for_learning}
          onChange={(assessment_for_learning) => setContent({ ...content, assessment_for_learning })}
        />
        <StringListEditor
          label="Common misconceptions"
          items={content.misconceptions}
          onChange={(misconceptions) => setContent({ ...content, misconceptions })}
        />

        <div>
          <h3 className="text-sm font-semibold text-slate-900">Differentiation</h3>
          <div className="mt-2 grid gap-3 sm:grid-cols-2">
            {(["support", "core", "challenge"] as const).map((tier) => (
              <div key={tier} className="flex flex-col gap-1">
                <label className="text-xs font-medium capitalize text-slate-600">{tier}</label>
                <textarea
                  value={content.differentiation?.[tier] ?? ""}
                  onChange={(e) =>
                    setContent({ ...content, differentiation: { ...content.differentiation, [tier]: e.target.value } })
                  }
                  rows={2}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                />
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Free-text teacher notes only — never a system-inferred diagnosis of a student's needs.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-900">Teacher notes</h3>
          <textarea
            value={content.teacher_notes ?? ""}
            onChange={(e) => setContent({ ...content, teacher_notes: e.target.value })}
            rows={3}
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          />
        </div>
      </fieldset>
    </main>
  );
}
