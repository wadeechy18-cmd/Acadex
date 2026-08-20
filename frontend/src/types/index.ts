export type EducationLevelSlug = "gcse" | "igcse" | "a-level" | "university";

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
