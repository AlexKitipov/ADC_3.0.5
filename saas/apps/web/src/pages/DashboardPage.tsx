import { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Activity,
  AlertTriangle,
  DollarSign,
  TrendingUp,
  Trophy,
} from 'lucide-react';
import { dashboardAPI } from '../api/dashboard';
import { LoadingState } from '../components/LoadingState';
import { StatCard } from '../components/StatCard';
import { DashboardStats, EquityPoint } from '../types';
import { formatCurrency, formatPercent } from '../lib/format';

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [equity, setEquity] = useState<EquityPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([dashboardAPI.getStats(), dashboardAPI.getEquityCurve(30)])
      .then(([statsResponse, equityResponse]) => {
        setStats(statsResponse.data);
        setEquity(equityResponse.data);
      })
      .catch((fetchError) => {
        console.error('Failed to fetch dashboard data:', fetchError);
        setError(
          'Failed to load dashboard data. Please refresh and try again.',
        );
      })
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading dashboard..." />;
  }

  if (error || !stats) {
    return (
      <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-100">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-6 w-6 text-rose-300" />
          <h2 className="text-xl font-semibold">Unable to load dashboard</h2>
        </div>
        <p className="mt-3 text-sm text-rose-200">
          {error ?? 'Dashboard stats were unavailable.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Dashboard</h2>
        <p className="mt-2 text-slate-400">
          Monitor account equity, drawdown, and trading outcomes.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Current Equity"
          value={formatCurrency(stats.current_equity)}
          icon={TrendingUp}
          tone="green"
          trend={stats.monthly_pnl >= 0 ? 'up' : 'down'}
        />
        <StatCard
          label="Total Balance"
          value={formatCurrency(stats.total_balance)}
          icon={DollarSign}
        />
        <StatCard
          label="Win Rate"
          value={formatPercent(stats.win_rate)}
          icon={Trophy}
          tone="amber"
        />
        <StatCard
          label="Total Trades"
          value={stats.total_trades.toString()}
          icon={Activity}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(22rem,1fr)]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="mb-6">
            <h3 className="text-xl font-semibold text-white">Equity Curve</h3>
            <p className="text-sm text-slate-400">
              Last 30 days of balance and equity snapshots.
            </p>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equity}>
                <defs>
                  <linearGradient id="equity" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(value) =>
                    new Date(value).toLocaleDateString()
                  }
                  stroke="#94a3b8"
                />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    background: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="#60a5fa"
                  fill="url(#equity)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <aside className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h3 className="text-xl font-semibold text-white">
            Performance Metrics
          </h3>
          <p className="mt-2 text-sm text-slate-400">
            Quick risk and profit indicators for the current month.
          </p>
          <div className="mt-6 divide-y divide-slate-800">
            <MetricRow
              label="Max Drawdown"
              value={formatPercent(stats.max_drawdown)}
            />
            <MetricRow
              label="Monthly P&L"
              value={formatCurrency(stats.monthly_pnl)}
              valueTone={stats.monthly_pnl >= 0 ? 'positive' : 'negative'}
            />
          </div>
        </aside>
      </section>
    </div>
  );
}

interface MetricRowProps {
  label: string;
  value: string;
  valueTone?: 'default' | 'positive' | 'negative';
}

function MetricRow({ label, value, valueTone = 'default' }: MetricRowProps) {
  const toneClass =
    valueTone === 'positive'
      ? 'text-emerald-300'
      : valueTone === 'negative'
        ? 'text-rose-300'
        : 'text-white';

  return (
    <div className="flex items-center justify-between py-4">
      <span className="text-sm text-slate-400">{label}</span>
      <span className={`font-semibold ${toneClass}`}>{value}</span>
    </div>
  );
}
