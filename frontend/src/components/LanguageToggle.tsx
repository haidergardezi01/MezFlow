"use client";

import { useAuthStore } from "@/lib/authStore";
import { Globe } from "lucide-react";

export function LanguageToggle() {
  const { language, setLanguage } = useAuthStore();

  const toggleLanguage = () => {
    const nextLang = language === "en" ? "ur" : "en";
    setLanguage(nextLang);
  };

  return (
    <button
      onClick={toggleLanguage}
      type="button"
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl glass-panel text-xs font-semibold text-slate-300 hover:text-white border border-white/10 hover:border-brand-500/30 transition-all"
      title="Switch Language (Urdu / English)"
    >
      <Globe className="w-3.5 h-3.5 text-brand-400" />
      <span>{language === "en" ? "اردو (Urdu)" : "English"}</span>
    </button>
  );
}
