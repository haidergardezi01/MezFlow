import Link from "next/link";
import {
  UtensilsCrossed,
  ChefHat,
  LayoutDashboard,
  QrCode,
  ArrowRight,
  Sparkles,
  Layers,
  Clock,
  CheckCircle2,
  LogIn,
} from "lucide-react";
import { LanguageToggle } from "@/components/LanguageToggle";

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col justify-between">
      {/* Top Header */}
      <nav className="w-full max-w-6xl mx-auto px-4 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400 font-bold text-sm">
            M
          </span>
          <span className="font-extrabold text-white text-lg tracking-tight">MezFlow</span>
        </div>
        <div className="flex items-center gap-3">
          <LanguageToggle />
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-brand-500/10 hover:bg-brand-500/20 text-brand-400 font-semibold text-xs border border-brand-500/30 transition-all shadow-sm"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </Link>
        </div>
      </nav>

      <main className="px-4 py-8 flex flex-col items-center justify-center max-w-6xl mx-auto my-auto">
        {/* Top Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full glass-panel text-xs font-medium text-brand-400 mb-8 border border-brand-500/20 shadow-lg shadow-brand-500/5">
          <Sparkles className="w-3.5 h-3.5 text-brand-400" />
          <span>MezFlow Real-Time Operations Platform</span>
        </div>

      {/* Main Title & Subtitle */}
      <div className="text-center max-w-3xl mb-12">
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">
          One Real-Time Flow from{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 via-brand-500 to-amber-300">
            Table to Kitchen
          </span>
        </h1>
        <p className="text-base sm:text-lg text-slate-300/80 leading-relaxed">
          Zero-install collaborative dining, software-only Kitchen Display System,
          and decoupled table turnover management for modern restaurants.
        </p>
      </div>

      {/* Portal Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mb-16">
        {/* Customer PWA Card */}
        <Link
          href="/r/demo-bistro/t/table-4"
          className="group glass-panel rounded-2xl p-7 glass-card-hover flex flex-col justify-between relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/10 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none group-hover:bg-brand-500/20 transition-all duration-300" />
          <div>
            <div className="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-5 group-hover:scale-110 transition-transform duration-200">
              <QrCode className="w-6 h-6" />
            </div>
            <span className="text-xs font-semibold uppercase tracking-wider text-brand-400">
              Module 2 & 3 • Customer PWA
            </span>
            <h2 className="text-xl font-bold text-white mt-1 mb-2.5">
              Diner Table Experience
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Scan-to-order mobile web app. Join a shared table session with live cart
              synchronization and per-diner attribution.
            </p>
          </div>
          <div className="flex items-center text-sm font-semibold text-brand-400 gap-1.5 group-hover:translate-x-1 transition-transform">
            <span>Open Table 4 Demo</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>

        {/* KDS Card */}
        <Link
          href="/kds"
          className="group glass-panel rounded-2xl p-7 glass-card-hover flex flex-col justify-between relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none group-hover:bg-blue-500/20 transition-all duration-300" />
          <div>
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-5 group-hover:scale-110 transition-transform duration-200">
              <ChefHat className="w-6 h-6" />
            </div>
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-400">
              Module 4 • Kitchen Display
            </span>
            <h2 className="text-xl font-bold text-white mt-1 mb-2.5">
              Kitchen Display System
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Paperless browser-based queue for cooks. Filter by station, advance order
              prep states, and watch real-time delay flags.
            </p>
          </div>
          <div className="flex items-center text-sm font-semibold text-blue-400 gap-1.5 group-hover:translate-x-1 transition-transform">
            <span>Launch Kitchen KDS</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>

        {/* Management Console Card */}
        <Link
          href="/admin"
          className="group glass-panel rounded-2xl p-7 glass-card-hover flex flex-col justify-between relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none group-hover:bg-purple-500/20 transition-all duration-300" />
          <div>
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 mb-5 group-hover:scale-110 transition-transform duration-200">
              <LayoutDashboard className="w-6 h-6" />
            </div>
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-400">
              Module 10 • Administration
            </span>
            <h2 className="text-xl font-bold text-white mt-1 mb-2.5">
              Management Console
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Admin dashboard for menu items, pricing, table QR codes, staff roles, and
              restaurant-level settings.
            </p>
          </div>
          <div className="flex items-center text-sm font-semibold text-purple-400 gap-1.5 group-hover:translate-x-1 transition-transform">
            <span>Enter Admin Portal</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </Link>
      </div>

      {/* Feature Badges Footer */}
      <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400 border-t border-slate-800/80 pt-8 w-full">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Independent Order & Table State Machines</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-400" />
          <span>Real-Time WebSocket Sync (&lt; 2s Latency)</span>
        </div>
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-brand-400" />
          <span>Multi-Tenant Architecture</span>
        </div>
      </div>
    </main>
    </div>
  );
}
