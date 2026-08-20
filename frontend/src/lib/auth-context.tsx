"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { apiFetch, clearTokens, getAccessToken, setTokens } from "@/lib/api-client";
import type { User, UserRole } from "@/types";

interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (params: {
    email: string;
    password: string;
    displayName: string;
    role: Extract<UserRole, "student" | "teacher">;
  }) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadCurrentUser() {
      const token = getAccessToken();
      if (!token) return;

      try {
        setUser(await apiFetch<User>("/auth/me", undefined, true));
      } catch {
        clearTokens();
      }
    }

    loadCurrentUser().finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string): Promise<User> {
    const data = await apiFetch<AuthTokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    return data.user;
  }

  async function register(params: {
    email: string;
    password: string;
    displayName: string;
    role: Extract<UserRole, "student" | "teacher">;
  }): Promise<User> {
    const data = await apiFetch<AuthTokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: params.email,
        password: params.password,
        display_name: params.displayName,
        role: params.role,
      }),
    });
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    return data.user;
  }

  function logout() {
    apiFetch("/auth/logout", { method: "POST" }, true).catch(() => {
      // best-effort; tokens are cleared client-side regardless
    });
    clearTokens();
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
