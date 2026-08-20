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
