"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import type {
  AbilityLevel,
  CurriculumSummary,
  CurriculumTopicSummary,
  KeyStageSummary,
  LessonPlan,
  Resource,
  SubjectSummary,
  YearGroupSummary,
} from "@/types";

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50";

const ABILITY_LEVELS: { value: AbilityLevel; label: string }[] = [
  { value: "mixed", label: "Mixed ability" },
  { value: "support", label: "Support" },
  { value: "core", label: "Core" },
  { value: "greater_depth", label: "Greater depth" },
];

export default function LessonPlannerPage() {
  const router = useRouter();

  const [curricula, setCurricula] = useState<CurriculumSummary[]>([]);
  const [keyStages, setKeyStages] = useState<KeyStageSummary[]>([]);
  const [yearGroups, setYearGroups] = useState<YearGroupSummary[]>([]);
  const [subjects, setSubjects] = useState<SubjectSummary[]>([]);
  const [topics, setTopics] = useState<CurriculumTopicSummary[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);

  const [curriculumId, setCurriculumId] = useState("");
  const [keyStageId, setKeyStageId] = useState("");
  const [yearGroupId, setYearGroupId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [topicId, setTopicId] = useState("");
  const [customTopicTitle, setCustomTopicTitle] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(45);
  const [abilityLevel, setAbilityLevel] = useState<AbilityLevel>("mixed");
  const [objectives, setObjectives] = useState("");
  const [instructions, setInstructions] = useState("");
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<CurriculumSummary[]>("/curriculum/curricula", undefined, true).then((list) => {
      setCurricula(list);
      if (list.length > 0) setCurriculumId(list[0].id);
    });
    apiFetch<Resource[]>("/resources", undefined, true).then(setResources);
  }, []);

  useEffect(() => {
    if (!curriculumId) return;
    setKeyStages([]);
    setKeyStageId("");
    apiFetch<KeyStageSummary[]>(`/curriculum/curricula/${curriculumId}/key-stages`, undefined, true).then(setKeyStages);
  }, [curriculumId]);

  useEffect(() => {
    if (!keyStageId) return;
    setYearGroups([]);
    setYearGroupId("");
    apiFetch<YearGroupSummary[]>(`/curriculum/key-stages/${keyStageId}/year-groups`, undefined, true).then(setYearGroups);
  }, [keyStageId]);

  useEffect(() => {
    if (!yearGroupId) return;
    setSubjects([]);
    setSubjectId("");
    apiFetch<SubjectSummary[]>(`/curriculum/year-groups/${yearGroupId}/subjects`, undefined, true).then(setSubjects);
  }, [yearGroupId]);

  useEffect(() => {
    if (!subjectId || !yearGroupId) return;
    setTopics([]);
    setTopicId("");
    apiFetch<CurriculumTopicSummary[]>(
      `/curriculum/topics?subject_id=${subjectId}&year_group_id=${yearGroupId}`,
      undefined,
      true
    ).then(setTopics);
  }, [subjectId, yearGroupId]);

  function toggleResource(id: string) {
    setSelectedResourceIds((prev) => (prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!subjectId || !yearGroupId) {
      setError("Choose a key stage, year group and subject first.");
      return;
    }
    if (!topicId && !customTopicTitle.trim()) {
      setError("Choose a curriculum topic or enter your own topic title.");
      return;
    }

    setSubmitting(true);
    try {
      const plan = await apiFetch<LessonPlan>(
        "/lesson-plans/generate",
        {
          method: "POST",
          body: JSON.stringify({
            subject_id: subjectId,
            year_group_id: yearGroupId,
            curriculum_topic_id: topicId || null,
            topic_title: topicId ? null : customTopicTitle,
            duration_minutes: durationMinutes,
            ability_level: abilityLevel,
            objectives: objectives || null,
            instructions: instructions || null,
            resource_ids: selectedResourceIds,
          }),
        },
        true
      );
      router.push(`/teacher/lesson-plans/${plan.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setError("AI lesson generation isn't configured on this server yet.");
      } else {
        setError(err instanceof ApiError ? err.message : "Couldn't generate a lesson plan.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-bold">AI Lesson Plan Builder</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Tell Acadex what you're teaching and it will draft a complete, structured lesson plan you can edit.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Curriculum</Label>
            <select className={selectClass} value={curriculumId} onChange={(e) => setCurriculumId(e.target.value)}>
              {curricula.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>Key stage</Label>
            <select className={selectClass} value={keyStageId} onChange={(e) => setKeyStageId(e.target.value)}>
              <option value="">Select...</option>
              {keyStages.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>Year group</Label>
            <select className={selectClass} value={yearGroupId} onChange={(e) => setYearGroupId(e.target.value)} disabled={!keyStageId}>
              <option value="">Select...</option>
              {yearGroups.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>Subject</Label>
            <select className={selectClass} value={subjectId} onChange={(e) => setSubjectId(e.target.value)} disabled={!yearGroupId}>
              <option value="">Select...</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <Label>Topic</Label>
          <select className={selectClass} value={topicId} onChange={(e) => setTopicId(e.target.value)} disabled={!subjectId}>
            <option value="">Enter my own topic below...</option>
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
          {!topicId && (
            <Input
              className="mt-2"
              placeholder="e.g. Fractions: halves and quarters"
              value={customTopicTitle}
              onChange={(e) => setCustomTopicTitle(e.target.value)}
            />
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Duration (minutes)</Label>
            <Input
              type="number"
              min={5}
              max={240}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
            />
          </div>
          <div>
            <Label>Ability level</Label>
            <select className={selectClass} value={abilityLevel} onChange={(e) => setAbilityLevel(e.target.value as AbilityLevel)}>
              {ABILITY_LEVELS.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <Label>Specific objectives (optional)</Label>
          <textarea
            className={`${selectClass} h-20`}
            value={objectives}
            onChange={(e) => setObjectives(e.target.value)}
            placeholder="Anything specific you want covered beyond the curriculum objectives"
          />
        </div>

        <div>
          <Label>Additional instructions (optional)</Label>
          <textarea
            className={`${selectClass} h-20`}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="e.g. include a practical group activity, avoid worksheets"
          />
        </div>

        {resources.length > 0 && (
          <div>
            <Label>Use these resources (optional)</Label>
            <div className="mt-2 flex flex-col gap-1 rounded-md border p-3">
              {resources.map((r) => (
                <label key={r.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedResourceIds.includes(r.id)}
                    onChange={() => toggleResource(r.id)}
                  />
                  {r.display_name}
                </label>
              ))}
            </div>
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" disabled={submitting}>
          {submitting ? "Generating…" : "Generate lesson plan"}
        </Button>
      </form>
    </main>
  );
}
