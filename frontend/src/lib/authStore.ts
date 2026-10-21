import { create } from "zustand";

export type UserRole =
  | "customer"
  | "kitchen_staff"
  | "service_staff"
  | "cashier"
  | "manager";

export interface UserProfile {
  id: string;
  display_name: string;
  preferred_language: "en" | "ur";
  push_notifications_enabled: boolean;
}

export interface User {
  id: string;
  restaurant_id: string;
  email?: string;
  phone_number?: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  profile?: UserProfile;
}

interface AuthState {
  token: string | null;
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  language: "en" | "ur";
  setAuth: (token: string, user: User) => void;
  setLanguage: (lang: "en" | "ur") => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("mezflow_token") : null,
  user: null,
  role: null,
  isAuthenticated:
    typeof window !== "undefined" ? !!localStorage.getItem("mezflow_token") : false,
  language: "en",

  setAuth: (token: string, user: User) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("mezflow_token", token);
      localStorage.setItem("mezflow_role", user.role);
      localStorage.setItem("mezflow_restaurant_id", user.restaurant_id);
    }
    set({
      token,
      user,
      role: user.role,
      isAuthenticated: true,
      language: user.profile?.preferred_language || "en",
    });
  },

  setLanguage: (lang: "en" | "ur") => {
    if (typeof document !== "undefined") {
      document.documentElement.dir = lang === "ur" ? "rtl" : "ltr";
      document.documentElement.lang = lang;
    }
    set({ language: lang });
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("mezflow_token");
      localStorage.removeItem("mezflow_role");
      localStorage.removeItem("mezflow_restaurant_id");
    }
    set({
      token: null,
      user: null,
      role: null,
      isAuthenticated: false,
    });
  },
}));
