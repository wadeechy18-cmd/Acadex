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
