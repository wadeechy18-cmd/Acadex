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
