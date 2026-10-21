import Link from "next/link";
import { ArrowLeft, Sparkles, ShoppingBag, Utensils } from "lucide-react";

export default function CustomerTablePage({
  params,
}: {
  params: { restaurantId: string; tableId: string };
}) {
  return (
    <div className="min-h-screen bg-surface-dark pb-24">
      {/* Top Header */}
      <header className="sticky top-0 z-30 glass-panel border-b border-surface-border px-4 py-3 flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Home</span>
        </Link>
        <div className="text-center">
          <h1 className="text-sm font-bold text-white uppercase tracking-wider">
            {params.restaurantId.replace("-", " ")}
          </h1>
          <span className="text-[11px] font-semibold text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded-full border border-brand-500/20">
            {params.tableId.replace("-", " ").toUpperCase()}
          </span>
        </div>
        <button
          type="button"
          aria-label="View Cart"
          className="relative p-2 rounded-xl glass-panel text-slate-300 hover:text-white"
        >
          <ShoppingBag className="w-5 h-5 text-brand-400" />
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-brand-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            0
          </span>
        </button>
      </header>

      {/* Hero Welcome */}
      <section className="px-4 py-6 max-w-lg mx-auto">
        <div className="glass-panel rounded-2xl p-5 border border-brand-500/20 relative overflow-hidden mb-6">
          <div className="flex items-center gap-2 text-xs font-semibold text-brand-400 mb-1">
            <Sparkles className="w-4 h-4" />
            <span>Collaborative Dining Session</span>
          </div>
          <h2 className="text-lg font-bold text-white mb-1">
            Welcome to Your Table
          </h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            Anyone at this table can scan and add dishes to the same shared cart in
            real time. You'll see who added each item.
          </p>
        </div>

        {/* Placeholder Categories & Items for M2 Foundation */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Utensils className="w-4 h-4 text-brand-400" />
            <span>Menu Preview (Module 2 Target)</span>
          </h3>
          <div className="glass-panel rounded-xl p-4 text-center text-xs text-slate-400 border border-dashed border-slate-700">
            Menu items, structured modifiers, and collaborative live cart will be
            rendered here when Module 2 is initialized.
          </div>
        </div>
      </section>
    </div>
  );
}
