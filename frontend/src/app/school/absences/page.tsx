"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { SchoolMember, TeacherAbsence } from "@/types";

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

const DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function SchoolAbsencesPage() {
  const { school } = useAuth();
  const [absences, setAbsences] = useState<TeacherAbsence[]>([]);
  const [members, setMembers] = useState<SchoolMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [teacherId, setTeacherId] = useState("");
  const [date, setDate] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function loadAbsences() {
    if (!school) return;
    setLoading(true);
    apiFetch<TeacherAbsence[]>(`/schools/${school.id}/absences`, undefined, true)
      .then(setAbsences)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load absences."))
      .finally(() => setLoading(false));
  }

  useEffect(loadAbsences, [school]);
  useEffect(() => {
    if (!school) return;
    apiFetch<SchoolMember[]>(`/schools/${school.id}/members`, undefined, true).then((all) => setMembers(all.filter((m) => m.role === "teacher")));
  }, [school]);

  async function handleReport(e: FormEvent) {
    e.preventDefault();
    if (!school || !teacherId || !date) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await apiFetch(
        `/schools/${school.id}/absences`,
        { method: "POST", body: JSON.stringify({ teacher_user_id: teacherId, date, reason: reason || null }) },
        true
      );
      setTeacherId("");
      setDate("");
      setReason("");
      loadAbsences();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Couldn't report this absence.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!school) return;
    await apiFetch(`/schools/${school.id}/absences/${id}`, { method: "DELETE" }, true);
    loadAbsences();
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Absences</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Report a teacher absence and Acadex will identify every lesson it affects from the live timetable.
      </p>

      <form onSubmit={handleReport} className="mt-6 flex max-w-xl flex-wrap items-end gap-3">
        <div>
          <Label htmlFor="absenceTeacher">Teacher</Label>
          <select id="absenceTeacher" className={selectClass} value={teacherId} onChange={(e) => setTeacherId(e.target.value)} required>
            <option value="">Select...</option>
            {members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.display_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="absenceDate">Date</Label>
          <Input id="absenceDate" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        </div>
        <div className="flex-1">
          <Label htmlFor="absenceReason">Reason (optional)</Label>
          <Input id="absenceReason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Reporting…" : "Report absence"}
        </Button>
      </form>
      {formError && <p className="mt-2 text-sm text-destructive">{formError}</p>}

      {loading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}

      {!loading && !error && absences.length === 0 && <p className="mt-8 text-sm text-muted-foreground">No absences reported.</p>}

      {!loading && !error && absences.length > 0 && (
        <div className="mt-8 flex flex-col gap-3">
          {absences.map((a) => (
            <div key={a.id} className="rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">
                    {a.teacher_name} · {a.date}
                  </p>
                  {a.reason && <p className="text-sm text-muted-foreground">{a.reason}</p>}
                  <p className="text-xs text-muted-foreground">Reported by {a.reported_by_name}</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => handleDelete(a.id)}>
                  Delete
                </Button>
              </div>
              <div className="mt-3">
                {a.affected_lessons.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No lessons affected on this date.</p>
                ) : (
                  <>
                    <p className="text-sm font-medium">Affected lessons ({a.affected_lessons.length})</p>
                    <ul className="mt-1 flex flex-col gap-1">
                      {a.affected_lessons.map((lesson) => (
                        <li key={lesson.id} className="text-sm text-muted-foreground">
                          {DAY_LABELS[lesson.day_of_week]} {lesson.time_slot_label} ({lesson.start_time.slice(0, 5)}-{lesson.end_time.slice(0, 5)}):{" "}
                          {lesson.subject_name}
                          {lesson.class_name && ` · ${lesson.class_name}`}
                          {lesson.room_name && ` · ${lesson.room_name}`}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
