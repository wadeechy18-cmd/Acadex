"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type {
  AcademicYear,
  ClassSubjectRequirement,
  ClassSummary,
  CurriculumSummary,
  GenerateTimetableResult,
  RequirementScheduleSummary,
  Room,
  SchoolMember,
  SubjectSummary,
  TimeSlot,
  TimetableEntry,
  TimetableSummary,
} from "@/types";

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

interface CellForm {
  timeSlotId: string;
  dayOfWeek: number;
  periodKey: string;
  entryId: string | null;
  teacherUserId: string;
  subjectId: string;
  classId: string;
  roomId: string;
}

export default function SchoolTimetablePage() {
  const { school } = useAuth();

  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([]);
  const [timetables, setTimetables] = useState<TimetableSummary[]>([]);
  const [selectedTimetableId, setSelectedTimetableId] = useState("");
  const [entries, setEntries] = useState<TimetableEntry[]>([]);
  const [members, setMembers] = useState<SchoolMember[]>([]);
  const [classes, setClasses] = useState<ClassSummary[]>([]);
  const [subjects, setSubjects] = useState<SubjectSummary[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [cellForm, setCellForm] = useState<CellForm | null>(null);
  const [cellError, setCellError] = useState<string | null>(null);

  const [viewTeacherId, setViewTeacherId] = useState("");

  const [requirements, setRequirements] = useState<ClassSubjectRequirement[]>([]);
  const [reqClassId, setReqClassId] = useState("");
  const [reqSubjectId, setReqSubjectId] = useState("");
  const [reqPeriods, setReqPeriods] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [generationSummary, setGenerationSummary] = useState<RequirementScheduleSummary[] | null>(null);

  // Setup forms
  const [yearName, setYearName] = useState("");
  const [yearStart, setYearStart] = useState("");
  const [yearEnd, setYearEnd] = useState("");
  const [roomName, setRoomName] = useState("");
  const [slotDay, setSlotDay] = useState(0);
  const [slotStart, setSlotStart] = useState("09:00");
  const [slotEnd, setSlotEnd] = useState("09:45");
  const [slotLabel, setSlotLabel] = useState("");
  const [timetableName, setTimetableName] = useState("");
  const [timetableYearId, setTimetableYearId] = useState("");

  function loadSetup() {
    if (!school) return;
    apiFetch<AcademicYear[]>(`/schools/${school.id}/academic-years`, undefined, true).then(setAcademicYears);
    apiFetch<Room[]>(`/schools/${school.id}/rooms`, undefined, true).then(setRooms);
    apiFetch<TimeSlot[]>(`/schools/${school.id}/time-slots`, undefined, true).then(setTimeSlots);
    apiFetch<TimetableSummary[]>(`/schools/${school.id}/timetables`, undefined, true).then(setTimetables);
    apiFetch<SchoolMember[]>(`/schools/${school.id}/members`, undefined, true).then((all) => setMembers(all.filter((m) => m.role === "teacher")));
    apiFetch<ClassSummary[]>(`/schools/${school.id}/classes`, undefined, true).then(setClasses);
    apiFetch<CurriculumSummary[]>("/curriculum/curricula", undefined, true).then((curricula) => {
      if (curricula.length > 0) {
        apiFetch<SubjectSummary[]>(`/curriculum/curricula/${curricula[0].id}/subjects`, undefined, true).then(setSubjects);
      }
    });
  }

  useEffect(loadSetup, [school]);

  function loadEntries(timetableId: string) {
    if (!school || !timetableId) return;
    apiFetch<TimetableEntry[]>(`/schools/${school.id}/timetables/${timetableId}/entries`, undefined, true)
      .then(setEntries)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load timetable entries."));
  }

  function loadRequirements(timetableId: string) {
    if (!school || !timetableId) return;
    apiFetch<ClassSubjectRequirement[]>(`/schools/${school.id}/timetables/${timetableId}/requirements`, undefined, true).then(setRequirements);
  }

  useEffect(() => {
    if (selectedTimetableId) {
      loadEntries(selectedTimetableId);
      loadRequirements(selectedTimetableId);
      setGenerationSummary(null);
    }
  }, [selectedTimetableId, school]);

  async function handleAddRequirement(e: FormEvent) {
    e.preventDefault();
    if (!school || !selectedTimetableId || !reqClassId || !reqSubjectId) return;
    await apiFetch(
      `/schools/${school.id}/timetables/${selectedTimetableId}/requirements`,
      { method: "POST", body: JSON.stringify({ class_id: reqClassId, subject_id: reqSubjectId, periods_per_week: reqPeriods }) },
      true
    );
    setReqClassId("");
    setReqSubjectId("");
    setReqPeriods(3);
    loadRequirements(selectedTimetableId);
  }

  async function handleDeleteRequirement(requirementId: string) {
    if (!school || !selectedTimetableId) return;
    await apiFetch(`/schools/${school.id}/timetables/${selectedTimetableId}/requirements/${requirementId}`, { method: "DELETE" }, true);
    loadRequirements(selectedTimetableId);
  }

  async function handleGenerate() {
    if (!school || !selectedTimetableId) return;
    if (entries.length > 0 && !confirm("This replaces every lesson currently on this timetable with a freshly generated schedule. Continue?")) {
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const result = await apiFetch<GenerateTimetableResult>(`/schools/${school.id}/timetables/${selectedTimetableId}/generate`, { method: "POST" }, true);
      setGenerationSummary(result.requirements_summary);
      loadEntries(selectedTimetableId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't generate a timetable.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleCreateYear(e: FormEvent) {
    e.preventDefault();
    if (!school) return;
    await apiFetch(`/schools/${school.id}/academic-years`, { method: "POST", body: JSON.stringify({ name: yearName, start_date: yearStart, end_date: yearEnd }) }, true);
    setYearName("");
    setYearStart("");
    setYearEnd("");
    loadSetup();
  }

  async function handleCreateRoom(e: FormEvent) {
    e.preventDefault();
    if (!school || !roomName.trim()) return;
    await apiFetch(`/schools/${school.id}/rooms`, { method: "POST", body: JSON.stringify({ name: roomName }) }, true);
    setRoomName("");
    loadSetup();
  }

  async function handleCreateSlot(e: FormEvent) {
    e.preventDefault();
    if (!school || !slotLabel.trim()) return;
    await apiFetch(
      `/schools/${school.id}/time-slots`,
      { method: "POST", body: JSON.stringify({ day_of_week: slotDay, start_time: `${slotStart}:00`, end_time: `${slotEnd}:00`, label: slotLabel }) },
      true
    );
    setSlotLabel("");
    loadSetup();
  }

  async function handleCreateTimetable(e: FormEvent) {
    e.preventDefault();
    if (!school || !timetableYearId || !timetableName.trim()) return;
    const created = await apiFetch<TimetableSummary>(
      `/schools/${school.id}/timetables`,
      { method: "POST", body: JSON.stringify({ academic_year_id: timetableYearId, name: timetableName }) },
      true
    );
    setTimetableName("");
    loadSetup();
    setSelectedTimetableId(created.id);
  }

  // Group time slots into grid rows keyed by (start_time,end_time), independent of day
  const gridRows = useMemo(() => {
    const rowMap = new Map<string, { key: string; start: string; end: string; label: string; slotsByDay: Map<number, TimeSlot> }>();
    for (const slot of timeSlots) {
      const key = `${slot.start_time}-${slot.end_time}`;
      if (!rowMap.has(key)) {
        rowMap.set(key, { key, start: slot.start_time, end: slot.end_time, label: slot.label, slotsByDay: new Map() });
      }
      rowMap.get(key)!.slotsByDay.set(slot.day_of_week, slot);
    }
    return Array.from(rowMap.values()).sort((a, b) => a.start.localeCompare(b.start));
  }, [timeSlots]);

  function entryForSlot(timeSlotId: string): TimetableEntry | undefined {
    return entries.find((e) => e.time_slot_id === timeSlotId);
  }

  function openCell(timeSlotId: string, dayOfWeek: number, periodKey: string) {
    const existing = entryForSlot(timeSlotId);
    setCellError(null);
    setCellForm({
      timeSlotId,
      dayOfWeek,
      periodKey,
      entryId: existing?.id ?? null,
      teacherUserId: existing?.teacher_user_id ?? "",
      subjectId: existing?.subject_id ?? "",
      classId: existing?.class_id ?? "",
      roomId: existing?.room_id ?? "",
    });
  }

  async function submitCell() {
    if (!school || !cellForm || !selectedTimetableId) return;
    if (!cellForm.teacherUserId || !cellForm.subjectId) {
      setCellError("Choose a teacher and a subject.");
      return;
    }
    setCellError(null);
    const body = JSON.stringify({
      time_slot_id: cellForm.timeSlotId,
      teacher_user_id: cellForm.teacherUserId,
      subject_id: cellForm.subjectId,
      class_id: cellForm.classId || null,
      room_id: cellForm.roomId || null,
    });
    try {
      if (cellForm.entryId) {
        await apiFetch(`/schools/${school.id}/timetables/${selectedTimetableId}/entries/${cellForm.entryId}`, { method: "PATCH", body }, true);
      } else {
        await apiFetch(`/schools/${school.id}/timetables/${selectedTimetableId}/entries`, { method: "POST", body }, true);
      }
      setCellForm(null);
      loadEntries(selectedTimetableId);
    } catch (err) {
      setCellError(err instanceof ApiError ? err.message : "Couldn't save this lesson.");
    }
  }

  async function deleteCellEntry() {
    if (!school || !cellForm?.entryId || !selectedTimetableId) return;
    await apiFetch(`/schools/${school.id}/timetables/${selectedTimetableId}/entries/${cellForm.entryId}`, { method: "DELETE" }, true);
    setCellForm(null);
    loadEntries(selectedTimetableId);
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Timetable</h1>
      <p className="mt-1 text-sm text-muted-foreground">Set up the school week, then build the timetable grid.</p>
      {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

      <details className="mt-6 rounded-lg border p-4">
        <summary className="cursor-pointer font-semibold">Setup: academic years, rooms, time slots</summary>
        <div className="mt-4 grid grid-cols-1 gap-6 sm:grid-cols-3">
          <form onSubmit={handleCreateYear} className="flex flex-col gap-2">
            <Label>Academic year</Label>
            <Input placeholder="e.g. 2025/2026" value={yearName} onChange={(e) => setYearName(e.target.value)} required />
            <Input type="date" value={yearStart} onChange={(e) => setYearStart(e.target.value)} required />
            <Input type="date" value={yearEnd} onChange={(e) => setYearEnd(e.target.value)} required />
            <Button type="submit" size="sm">
              Add year
            </Button>
            <ul className="mt-2 text-sm text-muted-foreground">
              {academicYears.map((y) => (
                <li key={y.id}>{y.name}</li>
              ))}
            </ul>
          </form>

          <form onSubmit={handleCreateRoom} className="flex flex-col gap-2">
            <Label>Room</Label>
            <Input placeholder="e.g. Room 12" value={roomName} onChange={(e) => setRoomName(e.target.value)} required />
            <Button type="submit" size="sm">
              Add room
            </Button>
            <ul className="mt-2 text-sm text-muted-foreground">
              {rooms.map((r) => (
                <li key={r.id}>{r.name}</li>
              ))}
            </ul>
          </form>

          <form onSubmit={handleCreateSlot} className="flex flex-col gap-2">
            <Label>Time slot</Label>
            <select className={selectClass} value={slotDay} onChange={(e) => setSlotDay(Number(e.target.value))}>
              {DAYS.map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <Input type="time" value={slotStart} onChange={(e) => setSlotStart(e.target.value)} required />
              <Input type="time" value={slotEnd} onChange={(e) => setSlotEnd(e.target.value)} required />
            </div>
            <Input placeholder="e.g. Period 1" value={slotLabel} onChange={(e) => setSlotLabel(e.target.value)} required />
            <Button type="submit" size="sm">
              Add time slot
            </Button>
          </form>
        </div>
      </details>

      <div className="mt-6 flex flex-wrap items-end gap-4">
        <form onSubmit={handleCreateTimetable} className="flex items-end gap-2">
          <div>
            <Label>New timetable: academic year</Label>
            <select className={selectClass} value={timetableYearId} onChange={(e) => setTimetableYearId(e.target.value)}>
              <option value="">Select...</option>
              {academicYears.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                </option>
              ))}
            </select>
          </div>
          <Input placeholder="Timetable name" value={timetableName} onChange={(e) => setTimetableName(e.target.value)} />
          <Button type="submit" size="sm">
            Create timetable
          </Button>
        </form>

        <div>
          <Label>Viewing timetable</Label>
          <select className={selectClass} value={selectedTimetableId} onChange={(e) => setSelectedTimetableId(e.target.value)}>
            <option value="">Select a timetable...</option>
            {timetables.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        {selectedTimetableId && (
          <div>
            <Label>Filter by teacher</Label>
            <select className={selectClass} value={viewTeacherId} onChange={(e) => setViewTeacherId(e.target.value)}>
              <option value="">All teachers</option>
              {members.map((m) => (
                <option key={m.user_id} value={m.user_id}>
                  {m.display_name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {selectedTimetableId && (
        <div className="mt-8 rounded-lg border p-4">
          <h2 className="font-semibold">Auto-generate the timetable</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Tell Acadex how many periods per week each class needs of each subject, then generate -- it fills the whole
            grid by itself, respecting teacher qualifications and availability. This is deterministic scheduling, not AI.
          </p>

          <form onSubmit={handleAddRequirement} className="mt-4 flex flex-wrap items-end gap-2">
            <div>
              <Label>Class</Label>
              <select className={selectClass} value={reqClassId} onChange={(e) => setReqClassId(e.target.value)}>
                <option value="">Select...</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Subject</Label>
              <select className={selectClass} value={reqSubjectId} onChange={(e) => setReqSubjectId(e.target.value)}>
                <option value="">Select...</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Periods/week</Label>
              <Input type="number" min={1} max={20} className="w-24" value={reqPeriods} onChange={(e) => setReqPeriods(Number(e.target.value))} />
            </div>
            <Button type="submit" size="sm">
              Add requirement
            </Button>
          </form>

          {requirements.length > 0 && (
            <div className="mt-4 flex flex-col gap-1">
              {requirements.map((r) => (
                <div key={r.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                  <span>
                    {r.class_name} · {r.subject_name} · {r.periods_per_week}/week
                  </span>
                  <Button size="sm" variant="outline" onClick={() => handleDeleteRequirement(r.id)}>
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          )}

          {classes.length === 0 && (
            <p className="mt-4 text-sm text-muted-foreground">
              No classes yet -- teachers add these from their own Classes page, then they'll appear here.
            </p>
          )}

          <Button className="mt-4" onClick={handleGenerate} disabled={generating || requirements.length === 0}>
            {generating ? "Generating…" : "Generate timetable"}
          </Button>

          {generationSummary && (
            <div className="mt-4 rounded-md border bg-muted/30 p-3 text-sm">
              <p className="font-medium">Generation results</p>
              <ul className="mt-2 flex flex-col gap-1">
                {generationSummary.map((s) => (
                  <li key={s.requirement_id} className={s.scheduled_periods < s.requested_periods ? "text-destructive" : ""}>
                    {s.class_name} · {s.subject_name}: scheduled {s.scheduled_periods} of {s.requested_periods} requested
                    {s.scheduled_periods < s.requested_periods && " -- add more qualified teachers, availability, or time slots to fill the rest."}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {selectedTimetableId && gridRows.length > 0 && (
        <div className="mt-8 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="border p-2 text-left">Time</th>
                {DAYS.map((d) => (
                  <th key={d} className="border p-2 text-left">
                    {d}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {gridRows.map((row) => (
                <tr key={row.key}>
                  <td className="border p-2 align-top font-medium">
                    {row.label}
                    <div className="text-xs text-muted-foreground">
                      {row.start.slice(0, 5)}-{row.end.slice(0, 5)}
                    </div>
                  </td>
                  {DAYS.map((_, dayIndex) => {
                    const slot = row.slotsByDay.get(dayIndex);
                    if (!slot) return <td key={dayIndex} className="border p-2 text-muted-foreground">-</td>;
                    const entry = entryForSlot(slot.id);
                    const dimmed = viewTeacherId && entry && entry.teacher_user_id !== viewTeacherId;
                    return (
                      <td
                        key={dayIndex}
                        className={`cursor-pointer border p-2 align-top hover:bg-accent ${dimmed ? "opacity-30" : ""}`}
                        onClick={() => openCell(slot.id, dayIndex, row.key)}
                      >
                        {entry ? (
                          <div>
                            <p className="font-medium">{entry.subject_name}</p>
                            <p className="text-xs text-muted-foreground">{entry.teacher_name}</p>
                            {entry.class_name && <p className="text-xs text-muted-foreground">{entry.class_name}</p>}
                            {entry.room_name && <p className="text-xs text-muted-foreground">{entry.room_name}</p>}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">+</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedTimetableId && gridRows.length === 0 && (
        <p className="mt-8 text-sm text-muted-foreground">Add time slots in Setup above to start building the grid.</p>
      )}

      {cellForm && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/40 p-4" onClick={() => setCellForm(null)}>
          <div className="w-full max-w-sm rounded-lg bg-background p-6 shadow-lg" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-semibold">{DAYS[cellForm.dayOfWeek]} · {cellForm.periodKey}</h2>
            <div className="mt-4 flex flex-col gap-3">
              <div>
                <Label>Teacher</Label>
                <select className={selectClass} value={cellForm.teacherUserId} onChange={(e) => setCellForm({ ...cellForm, teacherUserId: e.target.value })}>
                  <option value="">Select...</option>
                  {members.map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Subject</Label>
                <select className={selectClass} value={cellForm.subjectId} onChange={(e) => setCellForm({ ...cellForm, subjectId: e.target.value })}>
                  <option value="">Select...</option>
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Class (optional)</Label>
                <select className={selectClass} value={cellForm.classId} onChange={(e) => setCellForm({ ...cellForm, classId: e.target.value })}>
                  <option value="">None</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Room (optional)</Label>
                <select className={selectClass} value={cellForm.roomId} onChange={(e) => setCellForm({ ...cellForm, roomId: e.target.value })}>
                  <option value="">None</option>
                  {rooms.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>
              {cellError && <p className="text-sm text-destructive">{cellError}</p>}
              <div className="flex justify-between gap-2">
                <div className="flex gap-2">
                  <Button size="sm" onClick={submitCell}>
                    Save
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setCellForm(null)}>
                    Cancel
                  </Button>
                </div>
                {cellForm.entryId && (
                  <Button size="sm" variant="outline" onClick={deleteCellEntry}>
                    Remove
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
