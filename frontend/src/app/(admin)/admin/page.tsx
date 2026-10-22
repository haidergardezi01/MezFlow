import Link from "next/link";
import {
  ArrowLeft,
  LayoutDashboard,
  UtensilsCrossed,
  Users,
  QrCode,
  DollarSign,
  TrendingUp,
  Settings,
  ChefHat,
} from "lucide-react";

export default function AdminDashboardPage() {
  return (
    <div className="min-h-screen bg-surface-dark flex">
      {/* Sidebar Navigation */}
      <aside className="w-64 glass-panel border-r border-surface-border p-6 flex flex-col justify-between hidden md:flex">
        <div>
          <div className="flex items-center gap-2 mb-8">
            <LayoutDashboard className="w-6 h-6 text-purple-400" />
            <span className="font-extrabold text-white text-base">MezFlow Admin</span>
          </div>

          <nav className="space-y-1 text-sm">
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-2 rounded-xl bg-purple-500/10 text-purple-300 font-medium"
            >
              <TrendingUp className="w-4 h-4" />
              <span>Overview</span>
            </a>
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-card transition-colors"
            >
              <UtensilsCrossed className="w-4 h-4" />
              <span>Menu & Prices</span>
            </a>
            <Link
              href="/admin/tables"
              className="flex items-center gap-3 px-3 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-card transition-colors"
            >
              <QrCode className="w-4 h-4" />
              <span>Tables & QR Codes</span>
            </Link>
            <Link
              href="/kds"
              target="_blank"
              className="flex items-center gap-3 px-3 py-2 rounded-xl text-brand-400 hover:text-white hover:bg-brand-500/10 transition-colors font-medium"
            >
              <ChefHat className="w-4 h-4" />
              <span>Kitchen Display (KDS)</span>
            </Link>
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-card transition-colors"
            >
              <Users className="w-4 h-4" />
              <span>Staff Roles</span>
            </a>
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-card transition-colors"
            >
              <DollarSign className="w-4 h-4" />
              <span>Billing & Reports</span>
            </a>
          </nav>
        </div>

        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Home</span>
        </Link>
      </aside>

      {/* Main Content View */}
      <main className="flex-1 p-6 md:p-10">
        <header className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">
              Restaurant Management Console
            </h1>
            <p className="text-xs text-slate-400">
              Module 10 • Centralized configuration for menus, staff, tables, and settings.
            </p>
          </div>
          <Link
            href="/"
            className="md:hidden inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Home</span>
          </Link>
        </header>

        {/* Status Card Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="glass-panel p-5 rounded-xl border border-surface-border">
            <span className="text-xs text-slate-400 font-medium">Active Tables</span>
            <div className="text-2xl font-bold text-white mt-1">10 Configured</div>
          </div>
          <div className="glass-panel p-5 rounded-xl border border-surface-border">
            <span className="text-xs text-slate-400 font-medium">Menu Items</span>
            <div className="text-2xl font-bold text-white mt-1">24 Dishes</div>
          </div>
          <div className="glass-panel p-5 rounded-xl border border-surface-border">
            <span className="text-xs text-slate-400 font-medium">Staff Accounts</span>
            <div className="text-2xl font-bold text-white mt-1">5 Roles</div>
          </div>
          <div className="glass-panel p-5 rounded-xl border border-surface-border">
            <span className="text-xs text-slate-400 font-medium">System Status</span>
            <div className="text-sm font-semibold text-emerald-400 mt-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Database Online
            </div>
          </div>
        </div>

        <div className="glass-panel p-8 rounded-2xl border border-dashed border-slate-700 text-center">
          <Settings className="w-10 h-10 text-purple-400/60 mx-auto mb-3" />
          <h2 className="text-base font-bold text-white mb-1">
            Console Initialized
          </h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Role-based protection and CRUD APIs will be bound here as part of Module 10
            and Module 1.
          </p>
        </div>
      </main>
    </div>
  );
}
