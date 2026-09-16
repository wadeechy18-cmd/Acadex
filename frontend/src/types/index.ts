export type UserRole = "school_admin" | "teacher" | "student";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  display_name: string;
}

export type SchoolMembershipRole = "admin" | "teacher";

export interface SchoolSummary {
  id: string;
  name: string;
  my_role: SchoolMembershipRole;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  school: SchoolSummary | null;
}

export interface SchoolMember {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: SchoolMembershipRole;
  joined_at: string;
}

export type ResourceKind = "pdf" | "docx" | "pptx" | "image" | "text";
export type ExtractionStatus = "pending" | "done" | "failed" | "not_applicable";

export interface Resource {
  id: string;
  display_name: string;
  original_filename: string;
  content_type: string;
  kind: ResourceKind;
  file_size_bytes: number;
  extraction_status: ExtractionStatus;
  extraction_error: string | null;
  subject_id: string | null;
  year_group_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CurriculumSummary {
  id: string;
  code: string;
  name: string;
  country: string;
}

export interface KeyStageSummary {
  id: string;
  code: string;
  name: string;
  sort_order: number;
}

export interface YearGroupSummary {
  id: string;
  code: string;
  name: string;
  sort_order: number;
}

export interface SubjectSummary {
  id: string;
  code: string;
  name: string;
}

export interface CurriculumTopicSummary {
  id: string;
  title: string;
  sort_order: number;
}

export interface ObjectiveSummary {
  id: string;
  code: string;
  description: string;
}

export type AbilityLevel = "support" | "core" | "greater_depth" | "mixed";
export type GenerationKind = "full_generation" | "section_regeneration" | "manual_edit";

export interface TimelineEntry {
  start_minute: number;
  end_minute: number;
  activity: string;
  description: string;
}

export interface Differentiation {
  support: string;
  core: string;
  greater_depth: string;
}

export interface LessonPlanContent {
  title: string;
  overview: string;
  learning_objectives: string[];
  success_criteria: string[];
  key_vocabulary: string[];
  prior_knowledge: string;
  resources_needed: string[];
  starter: string;
  teacher_explanation: string;
  guided_practice: string;
  independent_practice: string;
  key_questions: string[];
  differentiation: Differentiation;
  assessment: string;
  misconceptions: string[];
  plenary: string;
  homework: string;
  cross_curricular_links: string;
  timeline: TimelineEntry[];
}

export interface WorksheetContent {
  title: string;
  instructions: string;
  recall_questions: string[];
  understanding_questions: string[];
  application_questions: string[];
  challenge_questions: string[];
}

export interface HomeworkContent {
  title: string;
  instructions: string;
  tasks: string[];
  estimated_minutes: number;
}

export interface TranslatedContent {
  lesson: LessonPlanContent;
  worksheet: WorksheetContent | null;
  homework: HomeworkContent | null;
}

export interface LessonPlanVersion {
  id: string;
  version_number: number;
  content: LessonPlanContent;
  worksheet: WorksheetContent | null;
  homework_task: HomeworkContent | null;
  translation_bn: TranslatedContent | null;
  generation_kind: GenerationKind;
  generation_notes: string | null;
  safeguarding_flagged: boolean;
  safeguarding_notes: string | null;
  resource_ids: string[];
  created_at: string;
}

export interface LessonPlan {
  id: string;
  subject_id: string;
  subject_name: string;
  year_group_id: string;
  year_group_name: string;
  topic_title: string;
  duration_minutes: number;
  ability_level: AbilityLevel;
  scheduled_date: string | null;
  class_id: string | null;
  class_name: string | null;
  created_at: string;
  current_version: LessonPlanVersion;
}

export interface LessonPlanSummary {
  id: string;
  subject_id: string;
  subject_name: string;
  year_group_id: string;
  year_group_name: string;
  topic_title: string;
  duration_minutes: number;
  ability_level: AbilityLevel;
  scheduled_date: string | null;
  class_id: string | null;
  class_name: string | null;
  owner_display_name: string;
  current_version_number: number;
  updated_at: string;
}

export interface ClassSummary {
  id: string;
  name: string;
  subject_id: string | null;
  subject_name: string | null;
  year_group_id: string | null;
  year_group_name: string | null;
}

export type TaskPriority = "low" | "medium" | "high";
export type TaskStatus = "pending" | "in_progress" | "completed";
export type EffectiveTaskStatus = TaskStatus | "overdue";

export interface Task {
  id: string;
  title: string;
  description: string | null;
  assigned_to_user_id: string;
  assigned_to_name: string;
  subject_id: string | null;
  subject_name: string | null;
  class_id: string | null;
  class_name: string | null;
  deadline: string;
  priority: TaskPriority;
  status: TaskStatus;
  effective_status: EffectiveTaskStatus;
  created_at: string;
}

export interface AcademicYear {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
}

export interface Room {
  id: string;
  name: string;
  capacity: number | null;
}

export interface TimeSlot {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  label: string;
}

export interface TimetableSummary {
  id: string;
  academic_year_id: string;
  name: string;
}

export interface TimetableEntry {
  id: string;
  time_slot_id: string;
  teacher_user_id: string;
  teacher_name: string;
  subject_id: string;
  subject_name: string;
  class_id: string | null;
  class_name: string | null;
  room_id: string | null;
  room_name: string | null;
}

export interface ClassSubjectRequirement {
  id: string;
  class_id: string;
  class_name: string;
  subject_id: string;
  subject_name: string;
  periods_per_week: number;
}

export interface RequirementScheduleSummary {
  requirement_id: string;
  class_name: string;
  subject_name: string;
  requested_periods: number;
  scheduled_periods: number;
}

export interface GenerateTimetableResult {
  entries: TimetableEntry[];
  requirements_summary: RequirementScheduleSummary[];
}

export type AvailabilityStatus = "available" | "unavailable";

export interface Qualification {
  id: string;
  subject_id: string;
  subject_name: string;
}

export interface AffectedLesson {
  id: string;
  timetable_entry_id: string;
  time_slot_label: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  subject_name: string;
  class_name: string | null;
  room_name: string | null;
}

export interface TeacherAbsence {
  id: string;
  teacher_user_id: string;
  teacher_name: string;
  date: string;
  reason: string | null;
  reported_by_name: string;
  affected_lessons: AffectedLesson[];
  created_at: string;
}

export type SubstitutionPlanStatus = "proposed" | "approved" | "rejected";
export type AssignmentStatus = "assigned" | "unfilled";

export interface SubstitutionAssignment {
  id: string;
  affected_lesson_id: string;
  subject_name: string;
  time_slot_label: string;
  status: AssignmentStatus;
  substitute_teacher_user_id: string | null;
  substitute_teacher_name: string | null;
  reason: string | null;
}

export interface SubstitutionPlan {
  id: string;
  teacher_absence_id: string;
  status: SubstitutionPlanStatus;
  assignments: SubstitutionAssignment[];
  approved_by_name: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface TimetableExceptionCover {
  id: string;
  date: string;
  timetable_entry_id: string;
  subject_name: string;
  time_slot_label: string;
  class_name: string | null;
  room_name: string | null;
  original_teacher_name: string;
  substitute_teacher_user_id: string | null;
  substitute_teacher_name: string | null;
  cover_lesson_plan_id: string | null;
  cover_lesson_plan_title: string | null;
  cover_lesson_plan_message: string | null;
}

export interface Notification {
  id: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
}
