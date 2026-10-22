"use client";

import React, { useState } from "react";
import { Check, Flame, Send, Loader2 } from "lucide-react";

interface BumpBarProps {
  status: string;
  onBump: () => Promise<void>;
}

export function BumpBar({ status, onBump }: BumpBarProps) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (loading) return;
    try {
      setLoading(true);
      await onBump();
    } finally {
      setLoading(false);
    }
  };

  const getButtonConfig = () => {
    switch (status) {
      case "NEW":
      case "CONFIRMED":
        return {
          label: "START PREPARING",
          color:
            "bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white shadow-blue-600/30",
          icon: Flame,
        };
      case "PREPARING":
        return {
          label: "MARK READY FOR SERVE",
          color:
            "bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 font-black shadow-amber-500/30",
          icon: Check,
        };
      case "READY":
        return {
          label: "DISPATCH / DELIVERED",
          color:
            "bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white shadow-emerald-600/30",
          icon: Send,
        };
      default:
        return {
          label: "BUMP",
          color: "bg-slate-700 text-white",
          icon: Check,
        };
    }
  };

  const config = getButtonConfig();
  const Icon = config.icon;

  return (
    <button
      type="button"
      disabled={loading}
      onClick={handleClick}
      className={`w-full min-h-[56px] px-4 py-3 rounded-2xl font-black text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg transition-all active:scale-[0.98] disabled:opacity-50 ${config.color}`}
    >
      {loading ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : (
        <>
          <Icon className="w-5 h-5 stroke-[2.5]" />
          <span>{config.label}</span>
        </>
      )}
    </button>
  );
}
