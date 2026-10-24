"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useAuthStore } from "@/lib/authStore";

export function SignOutButton({ className = "" }: { className?: string }) {
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);

  return (
    <button
      type="button"
      onClick={() => {
        logout();
        router.replace("/login");
      }}
      className={`inline-flex items-center gap-1.5 h-11 px-3 rounded-xl border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white hover:border-slate-500 transition-colors ${className}`}
    >
      <LogOut className="w-4 h-4" />
      <span>Sign out</span>
    </button>
  );
}
