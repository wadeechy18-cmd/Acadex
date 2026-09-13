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

export interface LessonPlanVersion {
  id: string;
  version_number: number;
  content: LessonPlanContent;
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
  created_at: string;
  current_version: LessonPlanVersion;
}

export interface LessonPlanSummary {
  id: string;
  subject_name: string;
  year_group_name: string;
  topic_title: string;
  duration_minutes: number;
  ability_level: AbilityLevel;
  current_version_number: number;
  updated_at: string;
}
