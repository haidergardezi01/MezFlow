"use client";

import React, { useState } from "react";
import { Users, Sparkles, Check, Loader2 } from "lucide-react";

interface DinerJoinModalProps {
  isOpen: boolean;
  tableName: string;
  restaurantName: string;
  isUrdu?: boolean;
  initialName?: string;
  initialColor?: string;
  onJoin: (displayName: string, avatarColor: string) => Promise<void>;
}

const AVATAR_PALETTE = [
  "#F59E0B", // Amber
  "#10B981", // Emerald
  "#3B82F6", // Blue
  "#EC4899", // Pink
  "#8B5CF6", // Purple
  "#06B6D4", // Cyan
  "#F97316", // Orange
];

export function DinerJoinModal({
  isOpen,
  tableName,
  restaurantName,
  isUrdu = false,
  initialName = "",
  initialColor = AVATAR_PALETTE[0],
  onJoin,
}: DinerJoinModalProps) {
  const [displayName, setDisplayName] = useState(initialName);
  const [selectedColor, setSelectedColor] = useState(initialColor || AVATAR_PALETTE[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const getInitials = (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return "🍽️";
    const parts = trimmed.split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return trimmed.slice(0, 2).toUpperCase();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = displayName.trim();
    if (!trimmed) {
      setError(
        isUrdu ? "براہ کرم اپنا نام درج کریں" : "Please enter your name"
      );
      return;
    }
    if (trimmed.length < 2) {
      setError(
        isUrdu
          ? "نام کم از کم 2 حروف کا ہونا چاہیے"
          : "Name must be at least 2 characters"
      );
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await onJoin(trimmed, selectedColor);
    } catch (err: any) {
      setError(err.message || "Failed to join session. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      <div className="w-full max-w-sm rounded-3xl glass-panel border border-surface-border p-6 shadow-2xl relative overflow-hidden">
        {/* Subtle decorative glow */}
        <div
          className="absolute -top-16 -right-16 w-36 h-36 rounded-full blur-3xl opacity-30 pointer-events-none"
          style={{ backgroundColor: selectedColor }}
        />

        {/* Modal Header */}
        <div className="text-center mb-6 relative">
          <div className="inline-flex items-center justify-center p-2.5 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 mb-3">
            <Users className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-black text-white tracking-tight">
            {isUrdu ? "ٹیبل گروپ میں شامل ہوں" : "Join Table Order"}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {isUrdu
              ? `${restaurantName} • ${tableName}`
              : `Ordering together at ${restaurantName} • ${tableName}`}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Avatar Preview & Initial */}
          <div className="flex flex-col items-center justify-center gap-2">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center text-white text-lg font-black shadow-lg transition-transform transform active:scale-95"
              style={{ backgroundColor: selectedColor }}
            >
              {getInitials(displayName)}
            </div>
            <span className="text-[11px] text-slate-400 font-medium">
              {isUrdu ? "آپ کا اوتار" : "Your Avatar Color"}
            </span>
          </div>

          {/* Color Palette Chips */}
          <div className="flex items-center justify-center gap-2.5">
            {AVATAR_PALETTE.map((color) => {
              const isSelected = selectedColor === color;
              return (
                <button
                  key={color}
                  type="button"
                  onClick={() => setSelectedColor(color)}
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                    isSelected
                      ? "ring-2 ring-white ring-offset-2 ring-offset-surface-dark scale-110 shadow-md"
                      : "opacity-70 hover:opacity-100 hover:scale-105"
                  }`}
                  style={{ backgroundColor: color }}
                  aria-label={`Select avatar color ${color}`}
                >
                  {isSelected && <Check className="w-4 h-4 text-white stroke-[3]" />}
                </button>
              );
            })}
          </div>

          {/* Display Name Input */}
          <div className="space-y-1.5">
            <label
              htmlFor="diner-name-input"
              className="block text-xs font-semibold text-slate-300"
            >
              {isUrdu ? "آپ کا نام" : "Your Name"}
            </label>
            <input
              id="diner-name-input"
              type="text"
              value={displayName}
              onChange={(e) => {
                setDisplayName(e.target.value);
                if (error) setError(null);
              }}
              placeholder={isUrdu ? "مثلاً: علی، خضر، طلحہ..." : "e.g. Sail, Khizar, Talha..."}
              maxLength={30}
              autoFocus
              className="w-full px-4 py-3 rounded-xl glass-panel border border-surface-border text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
            />
            <p className="text-[10px] text-slate-500">
              {isUrdu
                ? "یہ نام آپ کے ساتھیوں کو مشترکہ کارٹ پر نظر آئے گا"
                : "This name will appear next to the items you add to the shared cart"}
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs text-center font-medium">
              {error}
            </div>
          )}

          {/* Submit CTA */}
          <button
            type="submit"
            disabled={loading}
            className="w-full min-h-[48px] py-3 px-4 rounded-xl bg-brand-500 hover:bg-brand-600 active:bg-brand-700 text-white font-bold text-sm shadow-lg shadow-brand-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{isUrdu ? "شامل ہو رہے ہیں..." : "Joining Table..."}</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>{isUrdu ? "آرڈر شروع کریں" : "Start Ordering Together"}</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
