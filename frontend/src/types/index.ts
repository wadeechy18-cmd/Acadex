export type EducationLevelSlug = "gcse" | "igcse" | "a-level" | "university";

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

export interface Subject {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
}

export interface Course {
  id: string;
  title: string;
  slug: string;
  description?: string | null;
}
