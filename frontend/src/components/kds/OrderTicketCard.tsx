"use client";

import React from "react";
import {
  Clock,
  AlertTriangle,
  Flame,
  Utensils,
  Coffee,
  ChefHat,
  Check,
  User,
  FileText,
} from "lucide-react";
import { KDSOrderCard, ItemStatus } from "@/types/kds";
import { useElapsedTimer } from "@/hooks/useElapsedTimer";
import { BumpBar } from "./BumpBar";

interface OrderTicketCardProps {
  order: KDSOrderCard;
  onBump: (orderId: string) => Promise<void>;
  onToggleItemStatus: (
    orderId: string,
    itemId: string,
    currentStatus: ItemStatus
  ) => Promise<void>;
}

export function OrderTicketCard({
  order,
  onBump,
  onToggleItemStatus,
}: OrderTicketCardProps) {
  const { formattedTime, urgency } = useElapsedTimer(
    order.placed_at,
    order.target_prep_minutes || 15
  );

  const getStationIcon = (station: string) => {
    switch (station.toLowerCase()) {
      case "grill":
        return Flame;
      case "fry":
        return Utensils;
      case "beverage":
        return Coffee;
      default:
        return ChefHat;
    }
  };

  const getCardBorderUrgencyClass = () => {
    if (urgency === "DELAYED") {
      return "border-rose-500 bg-rose-950/20 shadow-rose-900/40 ring-1 ring-rose-500";
    }
    if (urgency === "WARNING") {
      return "border-amber-500/80 bg-amber-950/15 shadow-amber-900/30";
    }
    return "border-slate-800 bg-slate-900/90";
  };

  const getTimerBadgeClass = () => {
    if (urgency === "DELAYED") {
      return "bg-rose-500 text-white animate-pulse font-black";
    }
    if (urgency === "WARNING") {
      return "bg-amber-400 text-slate-950 font-black";
    }
    return "bg-slate-800 text-slate-300 font-bold";
  };

  return (
    <div
      className={`rounded-3xl border p-4 flex flex-col justify-between shadow-2xl transition-all duration-200 relative overflow-hidden ${getCardBorderUrgencyClass()}`}
    >
      {/* Top Header */}
      <div>
        <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-black text-white tracking-tight">
                #{order.display_number}
              </span>
              <span className="px-2.5 py-0.5 rounded-lg bg-brand-500/15 border border-brand-500/30 text-brand-300 font-extrabold text-xs">
                {order.table_name || `Table ${order.table_number}`}
              </span>
            </div>

            {order.placed_by_diner_name && (
              <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                <User className="w-3 h-3 text-slate-500" />
                <span>{order.placed_by_diner_name}</span>
              </p>
            )}
          </div>

          {/* Timer & Urgency Badge */}
          <div className="flex flex-col items-end gap-1">
            <div
              className={`px-2.5 py-1 rounded-xl text-xs flex items-center gap-1.5 shadow-sm ${getTimerBadgeClass()}`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>{formattedTime}</span>
            </div>

            {urgency === "DELAYED" && (
              <span className="text-[10px] font-black text-rose-400 uppercase tracking-wider flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                DELAYED
              </span>
            )}
          </div>
        </div>

        {/* Customer Kitchen Notes */}
        {order.notes && (
          <div className="mt-2.5 p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-1.5 leading-snug">
            <FileText className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
            <span className="italic font-medium">&quot;{order.notes}&quot;</span>
          </div>
        )}

        {/* Dish Items List */}
        <div className="py-3 space-y-3">
          {order.items.map((item) => {
            const StationIcon = getStationIcon(item.kitchen_station);
            const isDone = item.status === "READY";

            return (
              <div
                key={item.id}
                onClick={() =>
                  onToggleItemStatus(
                    order.id,
                    item.id,
                    isDone ? "PENDING" : "READY"
                  )
                }
                role="button"
                tabIndex={0}
                className={`p-2.5 rounded-2xl border transition-all cursor-pointer flex items-start justify-between gap-3 ${
                  isDone
                    ? "bg-slate-950/60 border-slate-800/80 opacity-60 line-through text-slate-500"
                    : "bg-slate-950/90 border-slate-800 hover:border-slate-700 hover:bg-slate-950"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-base font-black ${
                        isDone ? "text-slate-500" : "text-brand-400"
                      }`}
                    >
                      {item.quantity}x
                    </span>
                    <h4
                      className={`text-sm font-black truncate ${
                        isDone ? "text-slate-500" : "text-white"
                      }`}
                    >
                      {item.item_name}
                    </h4>
                  </div>

                  {/* Modifiers Highlighting */}
                  {item.modifiers && item.modifiers.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {item.modifiers.map((mod) => {
                        const isRemoval =
                          mod.option_name.toLowerCase().includes("no ") ||
                          mod.option_name.toLowerCase().includes("without");

                        return (
                          <span
                            key={mod.id}
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                              isRemoval
                                ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                                : "bg-amber-500/20 text-amber-300 border-amber-500/40"
                            }`}
                          >
                            {mod.option_name}
                          </span>
                        );
                      })}
                    </div>
                  )}

                  {/* Special Cooking Instructions */}
                  {item.special_instructions && (
                    <p className="text-[11px] font-bold text-amber-400 mt-1 italic">
                      📝 {item.special_instructions}
                    </p>
                  )}
                </div>

                {/* Right: Station Tag & Checkoff Indicator */}
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                  <div className="flex items-center gap-1 text-[10px] font-bold uppercase text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    <StationIcon className="w-3 h-3 text-brand-400" />
                    <span>{item.kitchen_station}</span>
                  </div>

                  {/* Quick Checkoff Tickbox */}
                  <div
                    className={`w-6 h-6 rounded-lg flex items-center justify-center transition-all border ${
                      isDone
                        ? "bg-emerald-600 border-emerald-500 text-white"
                        : "bg-slate-900 border-slate-700 text-transparent"
                    }`}
                  >
                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Card Footer Bump Bar */}
      <div className="pt-2">
        <BumpBar status={order.status} onBump={() => onBump(order.id)} />
      </div>
    </div>
  );
}
