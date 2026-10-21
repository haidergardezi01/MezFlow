import Link from "next/link";
import { ArrowLeft, ChefHat, Filter, RefreshCw } from "lucide-react";

export default function KitchenDisplayPage() {
  return (
    <div className="min-h-screen bg-surface-dark flex flex-col">
      {/* KDS Header Bar */}
      <header className="glass-panel border-b border-surface-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Home</span>
          </Link>
          <div className="h-4 w-px bg-slate-700" />
          <div className="flex items-center gap-2">
            <ChefHat className="w-5 h-5 text-blue-400" />
            <h1 className="text-base font-bold text-white tracking-wide">
              Kitchen Display System (KDS)
            </h1>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 glass-panel px-3 py-1.5 rounded-lg">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span>All Stations</span>
          </div>
          <button
            type="button"
            className="p-2 rounded-lg glass-panel text-slate-400 hover:text-white"
            title="Refresh Orders"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main KDS Area */}
      <main className="flex-1 p-6 flex items-center justify-center">
        <div className="text-center max-w-md glass-panel p-8 rounded-2xl border border-dashed border-slate-700">
          <ChefHat className="w-12 h-12 text-blue-400/60 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-white mb-2">
            Kitchen Queue Ready
          </h2>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Live order cards with status filters (New, Preparing, Ready, Delayed) and
            category routing will be managed here under Module 4.
          </p>
          <span className="inline-block text-[11px] font-semibold text-blue-400 bg-blue-500/10 px-3 py-1 rounded-full border border-blue-500/20">
            Awaiting Orders from Table Carts
          </span>
        </div>
      </main>
    </div>
  );
}
