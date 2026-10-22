"use client";

import React from "react";
import { Crown } from "lucide-react";

interface DinerBadgeProps {
  name: string;
  avatarColor: string;
  isHost?: boolean;
  isYou?: boolean;
  size?: "xs" | "sm" | "md";
  showLabel?: boolean;
  prefix?: string; // e.g. "Added by "
}

export function DinerBadge({
  name,
  avatarColor,
  isHost = false,
  isYou = false,
  size = "sm",
  showLabel = true,
  prefix = "",
}: DinerBadgeProps) {
  const getInitials = (n: string) => {
    const trimmed = (n || "").trim();
    if (!trimmed) return "🍽️";
    const parts = trimmed.split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return trimmed.slice(0, 2).toUpperCase();
  };

  const sizeClasses = {
    xs: {
      avatar: "w-4 h-4 text-[9px]",
      text: "text-[10px]",
      icon: "w-2.5 h-2.5",
    },
    sm: {
      avatar: "w-5 h-5 text-[10px]",
      text: "text-[11px]",
      icon: "w-3 h-3",
    },
    md: {
      avatar: "w-7 h-7 text-xs font-bold",
      text: "text-xs font-semibold",
      icon: "w-3.5 h-3.5",
    },
  }[size];

  return (
    <div className="inline-flex items-center gap-1.5 shrink-0">
      <div
        className={`${sizeClasses.avatar} rounded-full flex items-center justify-center text-white font-bold shadow-sm relative`}
        style={{ backgroundColor: avatarColor || "#F59E0B" }}
        title={`${name}${isHost ? " (Host)" : ""}${isYou ? " (You)" : ""}`}
      >
        {getInitials(name)}
        {isHost && (
          <span
            className="absolute -top-1 -right-1 text-amber-300 drop-shadow"
            title="Table Host"
          >
            <Crown className={sizeClasses.icon} />
          </span>
        )}
      </div>

      {showLabel && (
        <span className={`${sizeClasses.text} text-slate-300 truncate max-w-[120px]`}>
          {prefix}
          <span className={isYou ? "text-brand-300 font-semibold" : "text-slate-200"}>
            {isYou ? "You" : name}
          </span>
        </span>
      )}
    </div>
  );
}
