"use client";

import React, { useMemo } from "react";
import { ShoppingBag, ChevronUp, Users } from "lucide-react";
import { CartResponse, Diner } from "@/types/menu";

interface FloatingCartBarProps {
  cart: CartResponse | null;
  activeDiners: Diner[];
  currentDinerId?: string;
  isUrdu?: boolean;
  onOpenDrawer: () => void;
}

export function FloatingCartBar({
  cart,
  activeDiners,
  currentDinerId,
  isUrdu = false,
  onOpenDrawer,
}: FloatingCartBarProps) {
  if (!cart || cart.item_count === 0) return null;

  // Extract distinct diners who have items in the cart
  const cartContributors = useMemo(() => {
    const contributorIds = new Set<string>();
    const list: { id: string; name: string; color: string }[] = [];

    cart.items.forEach((item) => {
      if (!contributorIds.has(item.diner_id)) {
        contributorIds.add(item.diner_id);
        list.push({
          id: item.diner_id,
          name: item.diner_name,
          color: item.avatar_color,
        });
      }
    });

    return list;
  }, [cart.items]);

  const formattedTotal = Number(cart.total_amount).toLocaleString("en-PK", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });

  return (
    <div
      className="fixed bottom-4 left-0 right-0 z-40 px-4 max-w-lg mx-auto pointer-events-none animate-slide-up"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      <button
        type="button"
        onClick={onOpenDrawer}
        aria-label="Open Shared Cart"
        className="w-full pointer-events-auto p-3.5 rounded-2xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 active:scale-[0.99] text-white shadow-xl shadow-brand-500/30 border border-brand-400/30 flex items-center justify-between transition-all group"
      >
        {/* Left: Bag Icon & Item count badge */}
        <div className="flex items-center gap-3">
          <div className="relative p-2 rounded-xl bg-white/20 text-white shadow-inner">
            <ShoppingBag className="w-5 h-5" />
            <span className="absolute -top-1.5 -right-1.5 min-w-[20px] h-5 px-1 bg-amber-400 text-slate-950 text-[10px] font-black rounded-full flex items-center justify-center shadow-md">
              {cart.item_count}
            </span>
          </div>

          <div className="text-left rtl:text-right">
            <div className="text-xs font-black tracking-wide flex items-center gap-1.5">
              <span>{isUrdu ? "مشترکہ کارٹ" : "Shared Cart"}</span>
              <span className="text-[10px] font-normal text-brand-100 opacity-90">
                ({cart.item_count} {cart.item_count === 1 ? "item" : "items"})
              </span>
            </div>

            {/* Contributor Avatar Stack */}
            <div className="flex items-center gap-1 mt-0.5">
              <div className="flex -space-x-1.5 rtl:space-x-reverse overflow-hidden">
                {cartContributors.slice(0, 4).map((c) => (
                  <div
                    key={c.id}
                    className="w-4 h-4 rounded-full border border-brand-700 flex items-center justify-center text-[8px] font-black text-white"
                    style={{ backgroundColor: c.color }}
                    title={c.name}
                  >
                    {c.name.slice(0, 1).toUpperCase()}
                  </div>
                ))}
              </div>
              <span className="text-[10px] text-brand-100 font-medium">
                {cartContributors.length}{" "}
                {cartContributors.length === 1
                  ? isUrdu
                    ? "شخص"
                    : "diner"
                  : isUrdu
                  ? "افراد"
                  : "diners"}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Authoritative Total & Expand arrow */}
        <div className="flex items-center gap-2.5">
          <div className="text-right rtl:text-left">
            <div className="text-sm font-black tracking-tight text-white">
              <span className="text-xs font-semibold mr-0.5">
                {cart.currency || "PKR"}
              </span>
              <span>{formattedTotal}</span>
            </div>
            <span className="text-[10px] text-brand-200 block">
              {isUrdu ? "ٹیپ کر کے دیکھیں" : "Tap to review"}
            </span>
          </div>

          <div className="w-7 h-7 rounded-xl bg-white/15 flex items-center justify-center group-hover:bg-white/25 transition-colors">
            <ChevronUp className="w-4 h-4 text-white" />
          </div>
        </div>
      </button>
    </div>
  );
}
