import type { ReactElement, ReactNode } from 'react';
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
  TrendingDown,
  TrendingUp,
  Trophy,
} from 'lucide-react';
import { dashboardAPI } from '../api/dashboard';
import { LoadingState } from '../components/LoadingState';
import { StatCard } from '../components/StatCard';
import type { DashboardStats, DrawdownCurvePoint, EquityCurvePoint } from '../types';
import { formatCurrency, formatPercent } from '../lib/format';

interface DashboardLoadResult {
  stats: DashboardStats;
  equity: EquityCurvePoint[];
  drawdown: DrawdownCurvePoint[];
  warnings: string[];
}

export async function loadDashboardData(
  days = 30,
): Promise<DashboardLoadResult> {
  const [statsResult, equityResult, drawdownResult] = await Promise.allSettled([
    dashboardAPI.getStats(),
    dashboardAPI.getEquityCurve(days),
    dashboardAPI.getDrawdownCurve(days),
  ] as const);

  const warnings: string[] = [];

  if (statsResult.status === 'rejected') {
    throw new Error('Dashboard stats were unavailable.');
  }

  if (equityResult.status === 'rejected') {
    warnings.push('Equity curve data could not be loaded.');
  }

  if (drawdownResult.status === 'rejected') {
    warnings.push('Drawdown curve data could not be loaded.');
  }

  return {
    stats: statsResult.value.data,
    equity: equityResult.status === 'fulfilled' ? equityResult.value.data : [],
    drawdown:
      drawdownResult.status === 'fulfilled' ? drawdownResult.value.data : [],
    warnings,
  };
}

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [equity, setEquity] = useState<EquityCurvePoint[]>([]);
  const [drawdown, setDrawdown] = useState<DrawdownCurvePoint[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData()
      .then((dashboardData) => {
        setStats(dashboardData.stats);
        setEquity(dashboardData.equity);
        setDrawdown(dashboardData.drawdown);
        setWarnings(dashboardData.warnings);
      })
      .catch((fetchError) => {
        console.error('Failed to fetch dashboard data:', fetchError);
        setError(
          fetchError instanceof Error
            ? fetchError.message
            : 'Failed to load dashboard data. Please refresh and try again.',
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

      {warnings.length > 0 && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-100">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-300" />
            <h3 className="font-semibold">
              Some dashboard data is unavailable
            </h3>
          </div>
          <ul className="mt-2 list-disc space-y-1 pl-8 text-sm text-amber-100/90">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

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
        <div className="space-y-6">
          <ChartCard
            title="Equity Curve"
            description="Last 30 days of balance and equity snapshots."
            emptyMessage="No equity snapshots are available for this period."
            hasData={equity.length > 0}
          >
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
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
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
          </ChartCard>

          <ChartCard
            title="Drawdown Curve"
            description="Last 30 days of drawdown snapshots."
            emptyMessage="No drawdown snapshots are available for this period."
            hasData={drawdown.length > 0}
          >
            <AreaChart data={drawdown}>
              <defs>
                <linearGradient id="drawdown" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
                stroke="#94a3b8"
              />
              <YAxis
                tickFormatter={(value) => formatPercent(value)}
                stroke="#94a3b8"
              />
              <Tooltip
                formatter={(value) => formatPercent(Number(value))}
                contentStyle={{
                  background: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="#fb7185"
                fill="url(#drawdown)"
                strokeWidth={2}
              />
            </AreaChart>
          </ChartCard>
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
              icon={<TrendingDown className="h-4 w-4 text-rose-300" />}
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

interface ChartCardProps {
  title: string;
  description: string;
  emptyMessage: string;
  children: ReactElement;
  hasData: boolean;
}

function ChartCard({
  title,
  description,
  emptyMessage,
  children,
  hasData,
}: ChartCardProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-white">{title}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
      <div className="h-80">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-700 text-sm text-slate-400">
            {emptyMessage}
          </div>
        )}
      </div>
    </div>
  );
}

interface MetricRowProps {
  label: string;
  value: string;
  valueTone?: 'default' | 'positive' | 'negative';
  icon?: ReactNode;
}

function MetricRow({
  label,
  value,
  valueTone = 'default',
  icon,
}: MetricRowProps) {
  const toneClass =
    valueTone === 'positive'
      ? 'text-emerald-300'
      : valueTone === 'negative'
        ? 'text-rose-300'
        : 'text-white';

  return (
    <div className="flex items-center justify-between py-4">
      <span className="flex items-center gap-2 text-sm text-slate-400">
        {icon}
        {label}
      </span>
      <span className={`font-semibold ${toneClass}`}>{value}</span>
    </div>
  );
}
