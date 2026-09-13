"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AvailabilityStatus, CurriculumSummary, Qualification, SchoolMember, SubjectSummary, TimeSlot } from "@/types";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri"];

function TeacherManagePanel({ schoolId, teacherUserId }: { schoolId: string; teacherUserId: string }) {
  const [subjects, setSubjects] = useState<SubjectSummary[]>([]);
  const [qualifications, setQualifications] = useState<Qualification[]>([]);
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([]);
  const [availability, setAvailability] = useState<Record<string, AvailabilityStatus>>({});

  function load() {
    apiFetch<CurriculumSummary[]>("/curriculum/curricula", undefined, true).then((curricula) => {
      if (curricula.length > 0) {
        apiFetch<SubjectSummary[]>(`/curriculum/curricula/${curricula[0].id}/subjects`, undefined, true).then(setSubjects);
      }
    });
    apiFetch<Qualification[]>(`/schools/${schoolId}/teachers/${teacherUserId}/qualifications`, undefined, true).then(setQualifications);
    apiFetch<TimeSlot[]>(`/schools/${schoolId}/time-slots`, undefined, true).then(setTimeSlots);
    apiFetch<{ time_slot_id: string; status: AvailabilityStatus }[]>(
      `/schools/${schoolId}/teachers/${teacherUserId}/availability`,
      undefined,
      true
    ).then((records) => {
      const map: Record<string, AvailabilityStatus> = {};
      for (const r of records) map[r.time_slot_id] = r.status;
      setAvailability(map);
    });
  }

  useEffect(load, [schoolId, teacherUserId]);

  async function toggleQualification(subjectId: string) {
    const existing = qualifications.find((q) => q.subject_id === subjectId);
    if (existing) {
      await apiFetch(`/schools/${schoolId}/qualifications/${existing.id}`, { method: "DELETE" }, true);
    } else {
      await apiFetch(`/schools/${schoolId}/teachers/${teacherUserId}/qualifications`, { method: "POST", body: JSON.stringify({ subject_id: subjectId }) }, true);
    }
    load();
  }

  async function toggleAvailability(timeSlotId: string) {
    const current = availability[timeSlotId] ?? "available";
    const next: AvailabilityStatus = current === "available" ? "unavailable" : "available";
    await apiFetch(
      `/schools/${schoolId}/teachers/${teacherUserId}/availability`,
      { method: "PUT", body: JSON.stringify({ time_slot_id: timeSlotId, status: next }) },
      true
    );
    setAvailability((prev) => ({ ...prev, [timeSlotId]: next }));
  }

  return (
    <div className="mt-3 border-t pt-3">
      <p className="text-sm font-medium">Qualified subjects</p>
      <div className="mt-2 flex flex-wrap gap-3">
        {subjects.map((s) => (
          <label key={s.id} className="flex items-center gap-1 text-sm">
            <input type="checkbox" checked={qualifications.some((q) => q.subject_id === s.id)} onChange={() => toggleQualification(s.id)} />
            {s.name}
          </label>
        ))}
      </div>

      <p className="mt-4 text-sm font-medium">Availability (click to toggle)</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {timeSlots.map((slot) => {
          const status = availability[slot.id] ?? "available";
          return (
            <button
              key={slot.id}
              type="button"
              onClick={() => toggleAvailability(slot.id)}
              className={`rounded px-2 py-1 text-xs ${status === "available" ? "bg-green-100 text-green-800" : "bg-destructive/10 text-destructive"}`}
            >
              {DAY_LABELS[slot.day_of_week]} {slot.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function SchoolTeachersPage() {
  const { school } = useAuth();
  const [members, setMembers] = useState<SchoolMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [adding, setAdding] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [managingId, setManagingId] = useState<string | null>(null);

  function loadMembers() {
    if (!school) return;
    setLoading(true);
    apiFetch<SchoolMember[]>(`/schools/${school.id}/members`, undefined, true)
      .then(setMembers)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load teachers."))
      .finally(() => setLoading(false));
  }

  useEffect(loadMembers, [school]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!school) return;
    setFormError(null);
    setAdding(true);
    try {
      await apiFetch(`/schools/${school.id}/members`, { method: "POST", body: JSON.stringify({ email, role: "teacher" }) }, true);
      setEmail("");
      loadMembers();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Couldn't add that teacher.");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(memberId: string) {
    if (!school) return;
    await apiFetch(`/schools/${school.id}/members/${memberId}`, { method: "DELETE" }, true);
    loadMembers();
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Teachers</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Add a teacher who already has an Acadex account by their email.
      </p>

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && (
        <div className="mt-6 flex flex-col gap-2">
          {members.map((m) => (
            <div key={m.id} className="rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{m.display_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {m.email} · {m.role}
                  </p>
                </div>
                <div className="flex gap-2">
                  {m.role !== "admin" && (
                    <Button variant="outline" size="sm" onClick={() => setManagingId(managingId === m.user_id ? null : m.user_id)}>
                      {managingId === m.user_id ? "Close" : "Manage"}
                    </Button>
                  )}
                  {m.role !== "admin" && (
                    <Button variant="outline" size="sm" onClick={() => handleRemove(m.id)}>
                      Remove
                    </Button>
                  )}
                </div>
              </div>
              {managingId === m.user_id && school && <TeacherManagePanel schoolId={school.id} teacherUserId={m.user_id} />}
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleAdd} className="mt-8 flex max-w-sm flex-col gap-3 border-t pt-6">
        <Label htmlFor="email">Teacher email</Label>
        <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        {formError && <p className="text-sm text-destructive">{formError}</p>}
        <Button type="submit" disabled={adding} className="self-start">
          {adding ? "Adding…" : "Add teacher"}
        </Button>
      </form>
    </main>
  );
}
