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
