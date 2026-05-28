import { Activity, BarChart3, BookOpen, LogOut, Settings, ShieldCheck, Zap } from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3, description: 'Portfolio health' },
  { to: '/signals', label: 'Signals', icon: Zap, description: 'Live market ideas' },
  { to: '/trades', label: 'Trades', icon: Activity, description: 'Open and closed P&L' },
  { to: '/settings', label: 'Settings', icon: Settings, description: 'Risk controls' },
];

const footerLinks = [
  { label: 'Docs', href: '/docs' },
  { label: 'Status', href: '/status' },
  { label: 'Support', href: 'mailto:support@adc.trading' },
];

export function AppShell() {
  const { user, logout } = useAuthStore();
  const currentYear = new Date().getFullYear();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-slate-800 bg-slate-950/95 p-6 shadow-2xl shadow-slate-950/50 lg:flex lg:flex-col">
        <div className="rounded-3xl border border-brand-500/20 bg-brand-500/10 p-5">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-brand-500">ADC</p>
          <h1 className="mt-2 text-2xl font-bold">Trading Platform</h1>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            AI-driven crypto and forex intelligence with real-time execution visibility.
          </p>
        </div>

        <nav className="mt-8 space-y-3" aria-label="Primary navigation">
          {navItems.map(({ to, label, icon: Icon, description }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `group flex items-center gap-4 rounded-2xl border px-4 py-3 text-sm font-medium transition ${
                  isActive
                    ? 'border-brand-500/50 bg-brand-600 text-white shadow-lg shadow-brand-600/20'
                    : 'border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <span className="rounded-xl bg-slate-950/50 p-2 text-white transition group-hover:bg-slate-900">
                <Icon size={18} />
              </span>
              <span>
                <span className="block">{label}</span>
                <span className="block text-xs font-normal text-slate-400 group-hover:text-slate-300">{description}</span>
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-4">
          <div className="flex items-center gap-3">
            <span className="rounded-2xl bg-emerald-400/20 p-2 text-emerald-200">
              <ShieldCheck size={20} />
            </span>
            <div>
              <p className="text-sm font-semibold text-white">Risk guard active</p>
              <p className="text-xs text-emerald-100/80">Position limits and alerts are monitored.</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/80 px-4 py-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Welcome back</p>
              <p className="font-semibold">{user?.username ?? 'Trader'}</p>
            </div>
            <button
              type="button"
              onClick={logout}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
            >
              <LogOut size={16} />
              Sign out
            </button>
          </div>
          <nav className="mt-4 flex gap-2 overflow-x-auto lg:hidden" aria-label="Mobile navigation">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm ${
                    isActive ? 'bg-brand-600 text-white' : 'bg-slate-900 text-slate-300'
                  }`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
        <footer className="border-t border-slate-800 bg-slate-950/80 px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-semibold text-slate-200">ADC Trading Platform</p>
              <p>© {currentYear} ADC. Built for disciplined, data-led trading decisions.</p>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              {footerLinks.map(({ label, href }) => (
                <a key={label} href={href} className="inline-flex items-center gap-1 hover:text-white">
                  {label === 'Docs' && <BookOpen size={15} />}
                  {label}
                </a>
              ))}
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
