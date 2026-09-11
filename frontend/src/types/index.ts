export type UserRole = "student" | "teacher" | "admin";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  display_name: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface EducationLevel {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  order_index: number;
}

export interface ExamBoard {
  id: string;
  name: string;
  slug: string;
  education_level_id: string | null;
}

export interface Subject {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  order_index: number;
  education_level_id: string;
  exam_board_id: string | null;
}

export interface SubjectDetail extends Subject {
  courses: Course[];
}

export interface Course {
  id: string;
  subject_id: string;
  title: string;
  slug: string;
  description?: string | null;
  is_published: boolean;
  order_index: number;
}

export type LessonType = "video" | "notes" | "mixed";

export interface Lesson {
  id: string;
  topic_id: string;
  title: string;
  slug: string;
  lesson_type: LessonType;
  order_index: number;
  is_published: boolean;
}

export interface Topic {
  id: string;
  chapter_id: string;
  title: string;
  slug: string;
  description?: string | null;
  order_index: number;
  lessons: Lesson[];
}

export interface Chapter {
  id: string;
  course_id: string;
  title: string;
  slug: string;
  description?: string | null;
  order_index: number;
  topics: Topic[];
}

export interface CourseDetail extends Course {
  chapters: Chapter[];
}

export type EnrollmentStatus = "active" | "completed" | "dropped";

export interface Enrollment {
  id: string;
  course_id: string;
  status: EnrollmentStatus;
  enrolled_at: string;
}

export interface EnrollmentWithCourse extends Enrollment {
  course: Course;
  completion_percentage: number;
}

export interface Progress {
  id: string;
  topic_id: string;
  completion_percentage: number;
  last_position_seconds: number | null;
  completed_at: string | null;
}

export interface ProgressWithTopic extends Progress {
  topic: Topic;
}

export type BookmarkTargetType = "lesson" | "question" | "note";

export interface Bookmark {
  id: string;
  target_type: BookmarkTargetType;
  target_id: string;
  created_at: string;
}

export interface DashboardSummary {
  my_courses: EnrollmentWithCourse[];
  continue_learning: ProgressWithTopic | null;
  recent_progress: ProgressWithTopic[];
  bookmarks: Bookmark[];
}

export type VideoProvider = "mux" | "cloudflare_stream" | "youtube_unlisted" | "s3" | "local";

export interface Video {
  id: string;
  provider: VideoProvider;
  duration_seconds: number | null;
  playback_url: string | null;
}

export type NoteBlock =
  | { type: "heading"; text: string }
  | { type: "paragraph"; text: string }
  | { type: "formula"; latex: string }
  | { type: "key_point"; text: string }
  | { type: "example"; text: string }
  | { type: "exam_tip"; text: string }
  | { type: string; [key: string]: unknown };

export interface Note {
  id: string;
  title: string;
  content_blocks: NoteBlock[];
  order_index: number;
}

export interface LessonBreadcrumb {
  topic: Topic;
  chapter: Chapter;
  course: Course;
  subject: Subject;
}

export interface LessonDetail extends Lesson {
  video: Video | null;
  notes: Note[];
  breadcrumb: LessonBreadcrumb;
  my_progress: Progress | null;
}

export type QuestionType = "mcq" | "short_answer" | "numerical" | "true_false" | "structured";
export type Difficulty = "easy" | "medium" | "hard";

export interface QuestionOption {
  id: string;
  text: string;
  order_index: number;
}

export interface QuestionSafe {
  id: string;
  subject_id: string;
  exam_board_id: string | null;
  chapter_id: string | null;
  topic_id: string | null;
  question_type: QuestionType;
  difficulty: Difficulty;
  marks: number;
  prompt: string;
  options: QuestionOption[];
}

export interface AnswerCheckResult {
  is_correct: boolean | null;
  correct_answer: string | null;
  explanation: string | null;
}

export interface Quiz {
  id: string;
  topic_id: string | null;
  chapter_id: string | null;
  title: string;
  has_timer: boolean;
  time_limit_seconds: number | null;
  is_published: boolean;
}

export interface QuizDetail extends Quiz {
  questions: QuestionSafe[];
}

export interface QuizAttempt {
  id: string;
  quiz_id: string;
  started_at: string | null;
  submitted_at: string | null;
  score: number | null;
  percentage: number | null;
}

export interface QuizAnswerResult {
  question_id: string;
  student_answer: string | null;
  is_correct: boolean | null;
  correct_answer: string | null;
  explanation: string | null;
}

export interface QuizAttemptResult extends QuizAttempt {
  answers: QuizAnswerResult[];
}

export interface CommentAuthor {
  id: string;
  display_name: string;
  role: UserRole;
  is_verified_teacher: boolean;
}

export interface Comment {
  id: string;
  body: string;
  is_verified_teacher_answer: boolean;
  is_pinned: boolean;
  is_deleted: boolean;
  created_at: string;
  author: CommentAuthor;
  vote_score: number;
  my_vote: number | null;
  replies: Comment[];
}

export interface Discussion {
  id: string;
  topic_id: string | null;
  title: string;
  created_by_id: string;
  created_at: string;
}

export type QuestionThreadStatus = "open" | "answered" | "closed";

export interface QuestionThread {
  id: string;
  student_id: string;
  subject_id: string;
  topic_id: string | null;
  description: string | null;
  status: QuestionThreadStatus;
  created_at: string;
}

export interface QuestionImage {
  id: string;
  url: string;
}

export interface QuestionThreadDetail extends QuestionThread {
  images: QuestionImage[];
  comments: Comment[];
}

export interface StudentProgressRow {
  student: User;
  completion_percentage: number;
  enrolled_at: string;
}

export interface PlatformStats {
  total_users: number;
  total_students: number;
  total_teachers: number;
  total_admins: number;
  total_subjects: number;
  total_courses: number;
  total_published_courses: number;
  total_lessons: number;
  total_questions: number;
  total_quiz_attempts: number;
  total_discussions: number;
  total_question_threads: number;
  pending_reports: number;
}

export interface AdminUserRow {
  id: string;
  email: string;
  role: UserRole;
  display_name: string;
  is_active: boolean;
  is_verified: boolean;
  is_verified_teacher: boolean | null;
  created_at: string;
}

export interface TeacherRow {
  id: string;
  user_id: string;
  display_name: string;
  is_verified_teacher: boolean;
  subjects: Subject[];
}

export type ReportStatus = "pending" | "resolved" | "dismissed";
export type ReportTargetType = "comment" | "question_thread";

export interface AdminReportRow {
  id: string;
  reported_by_id: string;
  target_type: ReportTargetType;
  target_id: string;
  reason: string;
  status: ReportStatus;
  created_at: string;
}

export type PastPaperSessionType = "january" | "may_june" | "october_november";

export interface PastPaper {
  id: string;
  subject_id: string;
  exam_board_id: string | null;
  title: string;
  year: number;
  session: PastPaperSessionType;
  paper_number: string;
}

export type PastPaperResourceType = "official_link" | "licensed_document" | "original_solution";

export interface PastPaperResource {
  id: string;
  resource_type: PastPaperResourceType;
  label: string;
  external_url: string | null;
  storage_key: string | null;
}

export interface PastPaperQuestionLink {
  id: string;
  question_id: string;
  question_number: string;
  marks: number;
}

export interface PastPaperDetail extends PastPaper {
  resources: PastPaperResource[];
  paper_questions: PastPaperQuestionLink[];
}

export interface SearchResult {
  type: "subject" | "course" | "lesson" | "past_paper";
  id: string;
  title: string;
  subtitle: string | null;
  url: string;
}

export interface SearchResponse {
  results: SearchResult[];
}

export type NotificationType =
  | "comment_reply"
  | "teacher_answer"
  | "course_update"
  | "new_lesson"
  | "quiz_result"
  | "teacher_announcement";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}

export type OrganizationKind = "personal" | "school";
export type OrganizationRole = "owner" | "admin" | "teacher";

export interface Organization {
  id: string;
  kind: OrganizationKind;
  name: string;
  created_at: string;
  my_role: OrganizationRole;
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: OrganizationRole;
  joined_at: string;
}

export type YearGroup =
  | "nursery"
  | "reception"
  | "year_1"
  | "year_2"
  | "year_3"
  | "year_4"
  | "year_5"
  | "year_6"
  | "year_7"
  | "year_8"
  | "year_9"
  | "year_10"
  | "year_11"
  | "year_12"
  | "year_13";

export interface TeachingClass {
  id: string;
  organization_id: string;
  teacher_user_id: string;
  name: string;
  subject_name: string;
  year_group: YearGroup;
  key_stage: string;
  qualification: string | null;
  exam_board_name: string | null;
}

export type LessonPlanTemplateType =
  | "standard"
  | "practical"
  | "revision"
  | "exam_prep"
  | "new_topic"
  | "retrieval"
  | "assessment"
  | "review"
  | "double"
  | "short";

export type LessonPlanStatus = "draft" | "published";

export interface LessonPlan {
  id: string;
  organization_id: string;
  class_id: string;
  teacher_user_id: string;
  title: string;
  topic: string;
  duration_minutes: number;
  template_type: LessonPlanTemplateType;
  status: LessonPlanStatus;
  created_at: string;
  updated_at: string;
  latest_version_number: number;
}

export interface ContentBlock {
  type: "paragraph" | "activity_instruction";
  text: string;
}

export interface DifferentiationNotes {
  support?: string | null;
  core?: string | null;
  challenge?: string | null;
  send_notes?: string | null;
  eal_notes?: string | null;
}

export interface LessonSection {
  id: string;
  type: string;
  title: string;
  duration_minutes: number;
  body: ContentBlock[];
}

export interface LessonPlanContent {
  learning_objectives: string[];
  success_criteria: string[];
  prior_knowledge: string[];
  key_vocabulary: string[];
  sections: LessonSection[];
  differentiation: DifferentiationNotes | null;
  assessment_for_learning: string[];
  misconceptions: string[];
  teacher_notes: string | null;
  safeguarding_note: string | null;
}

export interface LessonPlanDetail extends LessonPlan {
  content: LessonPlanContent;
}

export interface LessonPlanVersionSummary {
  id: string;
  version_number: number;
  created_by_user_id: string | null;
  created_at: string;
}

export interface TimingSuggestion {
  label: string;
  action: "extend_section" | "add_section";
  section_id: string | null;
  extend_by_minutes: number | null;
  new_section: LessonSection | null;
}

export interface TimingCheck {
  total_minutes: number;
  planned_minutes: number;
  difference_minutes: number;
  status: "ok" | "under" | "over";
  suggestions: TimingSuggestion[];
}

export interface QualityIssue {
  severity: "info" | "warning";
  message: string;
}

export interface LessonPlanQualityReport {
  timing: TimingCheck;
  issues: QualityIssue[];
}

export type ResourceType =
  | "exam_specification"
  | "scheme_of_work"
  | "teacher_notes"
  | "lesson_resource"
  | "worksheet"
  | "past_paper"
  | "mark_scheme"
  | "practical_guide"
  | "curriculum_document"
  | "other";

export type ResourceVisibility = "private" | "organization";
export type ExtractionStatus = "pending" | "completed" | "failed";

export interface UsageSummary {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_estimated_cost_cents: number;
}

export interface Resource {
  id: string;
  organization_id: string;
  uploaded_by_user_id: string;
  file_name: string;
  resource_type: ResourceType;
  visibility: ResourceVisibility;
  subject_name: string | null;
  exam_board_name: string | null;
  qualification: string | null;
  year_group: YearGroup | null;
  topic: string | null;
  unit: string | null;
  source: string | null;
  extraction_status: ExtractionStatus;
  extraction_error: string | null;
  created_at: string;
}

export interface PracticeItem {
  id: string;
  group: string;
  prompt: string;
  marks: number;
  answer: string;
}

export interface PracticeSetContent {
  instructions: string | null;
  items: PracticeItem[];
}

export interface AnswerKeyEntry {
  id: string;
  group: string;
  prompt: string;
  marks: number;
  answer: string;
}

export interface AnswerKey {
  total_marks: number;
  entries: AnswerKeyEntry[];
}

export interface Worksheet {
  id: string;
  lesson_plan_id: string;
  title: string;
  content: PracticeSetContent;
  total_marks: number;
  estimated_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface Homework {
  id: string;
  lesson_plan_id: string;
  title: string;
  content: PracticeSetContent;
  total_marks: number;
  estimated_minutes: number;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export type DayOfWeek = "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday";

export const DAYS_OF_WEEK: DayOfWeek[] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export interface WeeklyPlanItemView {
  id: string;
  class_id: string;
  class_name: string;
  lesson_plan_id: string | null;
  topic: string | null;
  template_type: string | null;
  day_of_week: DayOfWeek;
  start_time: string; // "HH:MM:SS"
  duration_minutes: number;
}

export interface WeeklyPlanIssue {
  category: "conflict" | "overload" | "gap" | "repeated_topic" | "missing_assessment";
  severity: "info" | "warning";
  message: string;
  day_of_week: DayOfWeek | null;
  item_ids: string[];
}

export interface WeeklyPlan {
  id: string;
  organization_id: string;
  teacher_user_id: string;
  week_start_date: string;
  created_at: string;
}

export interface WeeklyPlanDetail extends WeeklyPlan {
  items: WeeklyPlanItemView[];
  issues: WeeklyPlanIssue[];
}
