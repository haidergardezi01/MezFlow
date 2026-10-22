"use client";

import React from "react";
import { MenuItem } from "@/types/menu";
import { Clock, Flame, Leaf, ShieldCheck, Plus, Ban, Sparkles } from "lucide-react";

interface DishCardProps {
  item: MenuItem;
  currency?: string;
  language?: "en" | "ur";
  onSelect: (item: MenuItem) => void;
}

export function DishCard({
  item,
  currency = "PKR",
  language = "en",
  onSelect,
}: DishCardProps) {
  const isUrdu = language === "ur";
  const displayName = isUrdu && item.name_ur ? item.name_ur : item.name;
  const displayDesc = isUrdu && item.description_ur ? item.description_ur : item.description;

  const formattedPrice = Number(item.price).toLocaleString();
  const currencyDisplay = isUrdu ? "روپیہ" : currency;

  const isSoldOut = !item.is_available;

  return (
    <div
      className={`relative group rounded-2xl p-4 transition-all duration-200 border ${
        isSoldOut
          ? "bg-surface-card/40 border-surface-border/50 opacity-70 grayscale-[60%]"
          : "glass-panel border-surface-border hover:border-brand-500/40 hover:shadow-lg hover:shadow-brand-500/5"
      }`}
    >
      <div className="flex flex-col sm:flex-row justify-between items-start gap-3">
        {/* Dish Info Column */}
        <div className="flex-1 min-w-0">
          {/* Badges Row */}
          <div className="flex flex-wrap items-center gap-1.5 mb-2">
            {item.dietary_tags?.includes("halal") && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                <ShieldCheck className="w-3 h-3" />
                <span>{isUrdu ? "حلال" : "Halal"}</span>
              </span>
            )}
            {item.dietary_tags?.includes("spicy") && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                <Flame className="w-3 h-3 text-amber-500" />
                <span>{isUrdu ? "تیز مرچ" : "Spicy"}</span>
              </span>
            )}
            {item.dietary_tags?.includes("vegetarian") && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-300 bg-emerald-400/10 px-2 py-0.5 rounded-full border border-emerald-400/20">
                <Leaf className="w-3 h-3" />
                <span>{isUrdu ? "سبزی" : "Veg"}</span>
              </span>
            )}
            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-400 bg-surface-dark/60 px-2 py-0.5 rounded-full border border-surface-border">
              <Clock className="w-3 h-3" />
              <span>
                {item.expected_prep_minutes} {isUrdu ? "منٹ" : "mins"}
              </span>
            </span>
          </div>

          {/* Dish Name */}
          <h3 className="text-base font-bold text-white group-hover:text-brand-300 transition-colors tracking-tight mb-1">
            {displayName}
          </h3>

          {/* Secondary Subtitle if bilingual */}
          {isUrdu ? (
            <p className="text-xs text-slate-500 font-sans mb-1.5">{item.name}</p>
          ) : (
            item.name_ur && (
              <p className="text-xs text-slate-500 font-arabic mb-1.5" dir="rtl">
                {item.name_ur}
              </p>
            )
          )}

          {/* Description */}
          {displayDesc && (
            <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-3">
              {displayDesc}
            </p>
          )}

          {/* Modifiers count indicator */}
          {item.modifier_groups && item.modifier_groups.length > 0 && (
            <div className="flex items-center gap-1.5 text-[11px] text-brand-400/80 mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>
                {isUrdu
                  ? `${item.modifier_groups.length} اختیارات دستیاب ہیں`
                  : `${item.modifier_groups.length} customization options`}
              </span>
            </div>
          )}
        </div>

        {/* Price & Action Column */}
        <div className="w-full sm:w-auto flex sm:flex-col justify-between items-center sm:items-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-surface-border/40">
          <div className="text-left sm:text-right">
            <span className="text-xs text-slate-400 block font-normal">
              {isUrdu ? "قیمت" : "Price"}
            </span>
            <div className="text-lg font-extrabold text-white">
              {isUrdu ? (
                <span>
                  {formattedPrice} <span className="text-xs text-brand-400 font-normal">{currencyDisplay}</span>
                </span>
              ) : (
                <span>
                  <span className="text-xs text-brand-400 font-normal mr-1">{currencyDisplay}</span>
                  {formattedPrice}
                </span>
              )}
            </div>
          </div>

          {isSoldOut ? (
            <div className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
              <Ban className="w-4 h-4" />
              <span>{isUrdu ? "ختم ہو گیا (Sold Out)" : "Sold Out"}</span>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => onSelect(item)}
              aria-label={`Customize ${item.name}`}
              className="min-h-[44px] px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-95 text-white text-xs font-bold transition-all shadow-md shadow-brand-500/20 inline-flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4 stroke-[2.5]" />
              <span>
                {item.modifier_groups && item.modifier_groups.length > 0
                  ? isUrdu ? "ترمیم و آرڈر" : "Customize & Add"
                  : isUrdu ? "شامل کریں" : "Add to Order"}
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
