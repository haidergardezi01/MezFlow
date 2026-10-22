"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import apiClient from "@/lib/api";
import { useAuthStore } from "@/lib/authStore";
import { useMenuRealtime, RealtimeMenuEvent } from "@/hooks/useMenuRealtime";
import { DishCard } from "@/components/customer/DishCard";
import { ModifierModal } from "@/components/customer/ModifierModal";
import {
  PublicMenuResponse,
  MenuCategory,
  MenuItem,
  TableLookup,
  SelectedModifier,
} from "@/types/menu";
import {
  ArrowLeft,
  ShoppingBag,
  Sparkles,
  Wifi,
  WifiOff,
  Languages,
  AlertTriangle,
  Loader2,
  Utensils,
  Search,
} from "lucide-react";

export default function CustomerTablePage() {
  const params = useParams();
  const restaurantSlugOrId = params.restaurantId as string;
  const tableTokenOrId = params.tableId as string;

  const { language, setLanguage } = useAuthStore();
  const isUrdu = language === "ur";

  // Data States
  const [tableInfo, setTableInfo] = useState<TableLookup | null>(null);
  const [menu, setMenu] = useState<PublicMenuResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active Category & Search
  const [activeCategory, setActiveCategory] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal State
  const [selectedDish, setSelectedDish] = useState<MenuItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Local cart session counter (Precursor to Module 3 live collaborative cart)
  const [cartItemsCount, setCartItemsCount] = useState(0);

  // Load Table & Menu
  useEffect(() => {
    let isMounted = true;

    async function loadDiningSession() {
      setLoading(true);
      setError(null);
      try {
        // 1. Resolve table QR token
        const tableRes = await apiClient.get<TableLookup>(
          `/tables/lookup/${tableTokenOrId}`
        );
        if (!isMounted) return;
        setTableInfo(tableRes.data);

        // 2. Load public menu for this restaurant
        const menuRes = await apiClient.get<PublicMenuResponse>(
          `/restaurants/${tableRes.data.restaurant_id}/menu?lang=${language}`
        );
        if (!isMounted) return;
        setMenu(menuRes.data);

        if (menuRes.data.categories.length > 0) {
          setActiveCategory(menuRes.data.categories[0].id);
        }
      } catch (err: any) {
        if (!isMounted) return;
        setError(
          err.message ||
            "Unable to verify table QR code. Please ask the waiter for assistance."
        );
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadDiningSession();
    return () => {
      isMounted = false;
    };
  }, [tableTokenOrId, language]);

  // Real-time WebSocket hook for live 86ing & price changes (< 2s)
  const handleRealtimeEvent = (evt: RealtimeMenuEvent) => {
    if (!menu) return;

    if (evt.event === "ITEM_AVAILABILITY_CHANGED" && evt.item_id) {
      setMenu((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          categories: prev.categories.map((cat) => ({
            ...cat,
            items: cat.items.map((item) =>
              item.id === evt.item_id
                ? { ...item, is_available: evt.is_available ?? item.is_available }
                : item
            ),
          })),
        };
      });
    } else if (evt.event === "MENU_ITEM_UPDATED" && evt.item_id) {
      setMenu((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          categories: prev.categories.map((cat) => ({
            ...cat,
            items: cat.items.map((item) =>
              item.id === evt.item_id
                ? {
                    ...item,
                    name: evt.name ?? item.name,
                    price: evt.price !== undefined ? evt.price : item.price,
                    is_available: evt.is_available ?? item.is_available,
                  }
                : item
            ),
          })),
        };
      });
    }
  };

  const { isConnected } = useMenuRealtime(
    tableInfo?.restaurant_id,
    handleRealtimeEvent
  );

  // Scrollspy observer for active category
  const categoryRefs = useRef<Record<string, HTMLElement | null>>({});

  const scrollToCategory = (catId: string) => {
    setActiveCategory(catId);
    const element = categoryRefs.current[catId];
    if (element) {
      const headerOffset = 130;
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth",
      });
    }
  };

  // Filtered dishes
  const filteredCategories = useMemo(() => {
    if (!menu) return [];
    if (!searchQuery.trim()) return menu.categories;

    const q = searchQuery.toLowerCase().trim();
    return menu.categories
      .map((cat) => ({
        ...cat,
        items: cat.items.filter(
          (i) =>
            i.name.toLowerCase().includes(q) ||
            (i.name_ur && i.name_ur.includes(q)) ||
            (i.description && i.description.toLowerCase().includes(q))
        ),
      }))
      .filter((cat) => cat.items.length > 0);
  }, [menu, searchQuery]);

  const handleOpenDish = (dish: MenuItem) => {
    setSelectedDish(dish);
    setIsModalOpen(true);
  };

  const handleAddToCart = (payload: {
    item: MenuItem;
    selectedModifiers: SelectedModifier[];
    specialInstructions: string;
    quantity: number;
    calculatedTotal: number;
  }) => {
    setCartItemsCount((prev) => prev + payload.quantity);
  };

  // Loading State
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-dark flex flex-col items-center justify-center p-6 text-center">
        <Loader2 className="w-10 h-10 text-brand-400 animate-spin mb-4" />
        <h2 className="text-base font-bold text-white mb-1">
          {isUrdu ? "ٹیبل مینو لوڈ ہو رہا ہے..." : "Loading Digital Menu..."}
        </h2>
        <p className="text-xs text-slate-400 max-w-xs">
          {isUrdu
            ? "ہم کچن کے لائیو مینو اور دستیابی کو سنک کر رہے ہیں"
            : "Connecting to live kitchen availability and prices"}
        </p>
      </div>
    );
  }

  // Error State (e.g. Invalid QR Code)
  if (error || !tableInfo) {
    return (
      <div className="min-h-screen bg-surface-dark flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mb-4">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <h2 className="text-lg font-bold text-white mb-2">
          {isUrdu ? "کیو آر کوڈ تصدیق ناکام" : "Table Access Failed"}
        </h2>
        <p className="text-xs text-slate-400 max-w-sm mb-6 leading-relaxed">
          {error || "We could not verify this tabletop QR code. It may have expired or been regenerated by restaurant staff."}
        </p>
        <div className="flex gap-3">
          <Link
            href="/"
            className="px-4 py-2.5 rounded-xl glass-panel text-xs text-slate-300 hover:text-white"
          >
            {isUrdu ? "مرکزی صفحہ" : "Back to Home"}
          </Link>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-4 py-2.5 rounded-xl bg-brand-500 text-xs font-bold text-white hover:bg-brand-600"
          >
            {isUrdu ? "دوبارہ کوشش کریں" : "Retry Scan"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-surface-dark text-slate-100 pb-28"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      {/* Top App Header */}
      <header className="sticky top-0 z-40 glass-panel border-b border-surface-border px-4 py-3 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-2.5">
          <Link
            href="/"
            className="p-1.5 rounded-lg glass-panel text-slate-400 hover:text-white transition-colors"
            aria-label="Home"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="text-sm font-extrabold text-white tracking-tight">
                {tableInfo.restaurant_name}
              </h1>
              {isConnected ? (
                <span
                  title="Live kitchen sync active (< 2s)"
                  className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"
                />
              ) : (
                <span
                  title="Reconnecting to kitchen live sync..."
                  className="w-2 h-2 rounded-full bg-amber-400"
                />
              )}
            </div>
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-brand-400">
              <span className="bg-brand-500/10 px-2 py-0.5 rounded-md border border-brand-500/20">
                {tableInfo.table_name || `Table ${tableInfo.table_number}`}
              </span>
            </div>
          </div>
        </div>

        {/* Right Controls: Language switch & Cart button */}
        <div className="flex items-center gap-2">
          {/* Language Toggle */}
          <button
            type="button"
            onClick={() => setLanguage(isUrdu ? "en" : "ur")}
            className="px-2.5 py-1.5 rounded-xl glass-panel text-xs font-semibold text-slate-300 hover:text-white border border-surface-border flex items-center gap-1.5"
            aria-label="Toggle Language"
          >
            <Languages className="w-3.5 h-3.5 text-brand-400" />
            <span>{isUrdu ? "English" : "اردو"}</span>
          </button>

          {/* Cart Icon */}
          <button
            type="button"
            aria-label="Shopping Cart"
            className="relative p-2.5 rounded-xl bg-brand-500/15 border border-brand-500/30 text-brand-300 hover:bg-brand-500/25 transition-all"
          >
            <ShoppingBag className="w-4 h-4" />
            {cartItemsCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-brand-500 text-white text-[10px] font-black rounded-full flex items-center justify-center shadow-md">
                {cartItemsCount}
              </span>
            )}
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-2xl mx-auto px-4 pt-4">
        {/* Real-time sync banner indicator */}
        <div className="flex items-center justify-between text-[11px] text-slate-400 mb-3 px-1">
          <div className="flex items-center gap-1.5">
            {isConnected ? (
              <span className="text-emerald-400 flex items-center gap-1 font-medium">
                <Wifi className="w-3 h-3" />
                <span>{isUrdu ? "کچن لائیو رابطہ فعال" : "Live Kitchen Sync Active"}</span>
              </span>
            ) : (
              <span className="text-amber-400 flex items-center gap-1 font-medium">
                <WifiOff className="w-3 h-3" />
                <span>{isUrdu ? "دوبارہ رابطہ کیا جا رہا ہے..." : "Reconnecting Live Sync..."}</span>
              </span>
            )}
          </div>
          <span className="text-[10px] text-slate-500">
            {isUrdu ? "قیمتیں و دستیابی حقیقی وقت میں" : "Prices & 86ing synced in real time"}
          </span>
        </div>

        {/* Search Bar */}
        <div className="relative mb-4">
          <Search className="w-4 h-4 absolute top-3.5 left-3.5 text-slate-400 rtl:right-3.5 rtl:left-auto" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={
              isUrdu
                ? "ڈش تلاش کریں (مثلاً: کباب، کڑاہی، برگر)..."
                : "Search dishes (e.g. kebab, wings, karahi)..."
            }
            className="w-full text-xs pl-10 pr-4 rtl:pr-10 rtl:pl-4 py-3 rounded-2xl glass-panel border border-surface-border focus:border-brand-500 focus:outline-none text-white placeholder-slate-500"
          />
        </div>

        {/* Sticky Category Pill Bar with Scrollspy (WP2.8) */}
        {menu && menu.categories.length > 0 && (
          <div className="sticky top-[57px] z-30 -mx-4 px-4 py-2.5 bg-surface-dark/95 backdrop-blur-md border-b border-surface-border/60 overflow-x-auto scrollbar-none flex gap-2">
            {menu.categories.map((cat) => {
              const catName = isUrdu && cat.name_ur ? cat.name_ur : cat.name;
              const isActive = activeCategory === cat.id;

              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => scrollToCategory(cat.id)}
                  className={`min-h-[38px] px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                    isActive
                      ? "bg-brand-500 text-white shadow-md shadow-brand-500/20 scale-105"
                      : "glass-panel border-surface-border text-slate-400 hover:text-white"
                  }`}
                >
                  {catName}
                </button>
              );
            })}
          </div>
        )}

        {/* Categories & Dishes Section */}
        <div className="space-y-8 mt-5">
          {filteredCategories.map((category) => {
            const catName = isUrdu && category.name_ur ? category.name_ur : category.name;
            const catDesc =
              isUrdu && category.description_ur
                ? category.description_ur
                : category.description;

            return (
              <section
                key={category.id}
                ref={(el) => {
                  categoryRefs.current[category.id] = el;
                }}
                className="space-y-3 scroll-mt-36"
              >
                <div>
                  <h2 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
                    <Utensils className="w-4 h-4 text-brand-400" />
                    <span>{catName}</span>
                  </h2>
                  {catDesc && (
                    <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                      {catDesc}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {category.items.map((item) => (
                    <DishCard
                      key={item.id}
                      item={item}
                      currency={menu?.currency || "PKR"}
                      language={language}
                      onSelect={handleOpenDish}
                    />
                  ))}
                </div>
              </section>
            );
          })}

          {filteredCategories.length === 0 && (
            <div className="glass-panel p-8 rounded-2xl text-center border border-dashed border-slate-700 my-8">
              <Search className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <h3 className="text-sm font-bold text-white mb-1">
                {isUrdu ? "کوئی ڈش نہیں ملی" : "No Dishes Found"}
              </h3>
              <p className="text-xs text-slate-400">
                {isUrdu
                  ? "براہ کرم کوئی دوسرا لفظ تلاش کریں"
                  : "Try searching with a different term"}
              </p>
            </div>
          )}
        </div>
      </main>

      {/* Interactive Dish Customization Bottom Sheet Modal (WP2.10) */}
      <ModifierModal
        item={selectedDish}
        currency={menu?.currency || "PKR"}
        language={language}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onAddToCart={handleAddToCart}
      />
    </div>
  );
}
