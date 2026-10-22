"use client";

import React, { useState } from "react";
import { Send, AlertTriangle, Loader2, X, ChefHat, Check } from "lucide-react";
import { CartResponse } from "@/types/menu";

interface SubmitOrderModalProps {
  isOpen: boolean;
  cart: CartResponse | null;
  tableName: string;
  isUrdu?: boolean;
  isSubmitting?: boolean;
  onClose: () => void;
  onConfirm: (notes: string) => Promise<void>;
}

export function SubmitOrderModal({
  isOpen,
  cart,
  tableName,
  isUrdu = false,
  isSubmitting = false,
  onClose,
  onConfirm,
}: SubmitOrderModalProps) {
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !cart) return null;

  const formattedTotal = Number(cart.total_amount).toLocaleString("en-PK");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError(null);
      await onConfirm(notes.trim());
    } catch (err: any) {
      setError(err.message || "Failed to submit order. Please try again.");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      <div className="w-full max-w-md rounded-3xl glass-panel border border-surface-border p-6 shadow-2xl relative overflow-hidden">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={isSubmitting}
          aria-label="Close"
          className="absolute top-4 right-4 rtl:left-4 rtl:right-auto w-8 h-8 rounded-full glass-panel flex items-center justify-center text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header */}
        <div className="text-center mb-5">
          <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-brand-500/15 border border-brand-500/25 text-brand-400 mb-3">
            <ChefHat className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-black text-white tracking-tight">
            {isUrdu ? "کچن کو آرڈر بھیجیں؟" : "Send Order to Kitchen?"}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {isUrdu
              ? `${tableName} کے لیے ${cart.item_count} اشیاء کچن میں تیار ہونے کے لیے جائیں گی`
              : `${cart.item_count} items for ${tableName} will be fired directly to the kitchen`}
          </p>
        </div>

        {/* Order Quick Summary Card */}
        <div className="rounded-2xl glass-panel border border-surface-border p-4 mb-4 space-y-2">
          <div className="flex justify-between items-center text-xs text-slate-400">
            <span>{isUrdu ? "کل آئٹمز" : "Total Items"}</span>
            <span className="font-bold text-white">{cart.item_count}</span>
          </div>

          <div className="flex justify-between items-center text-sm font-black text-white pt-2 border-t border-surface-border/50">
            <span>{isUrdu ? "کل رقم" : "Total Amount"}</span>
            <span className="text-brand-400">
              {cart.currency || "PKR"} {formattedTotal}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Kitchen Notes Input */}
          <div className="space-y-1.5">
            <label
              htmlFor="kitchen-notes-input"
              className="block text-xs font-semibold text-slate-300"
            >
              {isUrdu
                ? "کچن کے لیے خصوصی ہدایات (اختیاری)"
                : "Kitchen / Serving Notes (Optional)"}
            </label>
            <textarea
              id="kitchen-notes-input"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={
                isUrdu
                  ? "مثلاً: پہلے اسٹارٹرز لائیں، اضافی چمچ اور پانی..."
                  : "e.g. Please bring appetizers first, extra plates..."
              }
              maxLength={250}
              className="w-full px-3.5 py-2.5 rounded-xl glass-panel border border-surface-border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors resize-none"
            />
          </div>

          {/* Warning Banner */}
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] leading-relaxed">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              {isUrdu
                ? "تصدیق کے بعد کارٹ محفوظ ہو جائے گا اور شیف فوری طور پر کھانا پکانا شروع کر دیں گے۔"
                : "Once confirmed, the cart will lock and the chefs will begin cooking immediately."}
            </span>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs text-center font-medium">
              {error}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 py-3 px-4 rounded-xl glass-panel text-slate-300 hover:text-white font-bold text-xs transition-colors disabled:opacity-50"
            >
              {isUrdu ? "واپس جائیں" : "Back to Cart"}
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 min-h-[46px] py-3 px-4 rounded-xl bg-brand-500 hover:bg-brand-600 active:bg-brand-700 text-white font-bold text-xs shadow-lg shadow-brand-500/25 flex items-center justify-center gap-1.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{isUrdu ? "بھیج رہے ہیں..." : "Sending..."}</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 rtl:-scale-x-100" />
                  <span>{isUrdu ? "تصدیق کریں" : "Confirm & Fire"}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
