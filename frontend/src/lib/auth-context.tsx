"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiFetch, ApiError, clearTokens, getAccessToken, setTokens } from "@/lib/api-client";
import type { AuthResponse, SchoolSummary, User } from "@/types";

interface MeResponse {
  user: User;
  school: SchoolSummary | null;
}

interface AuthContextValue {
  user: User | null;
  school: SchoolSummary | null;
  loading: boolean;
  registerTeacher: (params: { email: string; password: string; displayName: string }) => Promise<void>;
  registerSchool: (params: {
    schoolName: string;
    adminEmail: string;
    adminPassword: string;
    adminDisplayName: string;
  }) => Promise<void>;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [school, setSchool] = useState<SchoolSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiFetch<MeResponse>("/auth/me", undefined, true)
      .then((res) => {
        setUser(res.user);
        setSchool(res.school);
      })
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  function applyAuthResponse(res: AuthResponse) {
    setTokens(res.access_token, res.refresh_token);
    setUser(res.user);
    setSchool(res.school);
  }

  async function registerTeacher(params: { email: string; password: string; displayName: string }) {
    const res = await apiFetch<AuthResponse>("/auth/register/teacher", {
      method: "POST",
      body: JSON.stringify({ email: params.email, password: params.password, display_name: params.displayName }),
    });
    applyAuthResponse(res);
  }

  async function registerSchool(params: {
    schoolName: string;
    adminEmail: string;
    adminPassword: string;
    adminDisplayName: string;
  }) {
    const res = await apiFetch<AuthResponse>("/auth/register/school", {
      method: "POST",
      body: JSON.stringify({
        school_name: params.schoolName,
        admin_email: params.adminEmail,
        admin_password: params.adminPassword,
        admin_display_name: params.adminDisplayName,
      }),
    });
    applyAuthResponse(res);
  }

  async function login(email: string, password: string): Promise<User> {
    const res = await apiFetch<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    applyAuthResponse(res);
    return res.user;
  }

  function logout() {
    clearTokens();
    setUser(null);
    setSchool(null);
  }

  return (
    <AuthContext.Provider value={{ user, school, loading, registerTeacher, registerSchool, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

export { ApiError };
