import type { ReactElement, ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
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
  ArrowRight,
  DollarSign,
  Settings,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Trophy,
} from 'lucide-react';
import { dashboardAPI } from '../api/dashboard';
import { LiveMarketWidget } from '../components/LiveMarketWidget';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/PageState';
import { SessionControls } from '../components/SessionControls';
import { StatCard } from '../components/StatCard';
import type { DashboardStats, DrawdownCurvePoint, EquityCurvePoint } from '../types';
import { formatCurrency, formatPercent } from '../lib/format';

type NormalizedDashboardStats = {
  [Key in keyof DashboardStats]: number;
};

interface DashboardLoadResult {
  stats: NormalizedDashboardStats;
  equity: EquityCurvePoint[];
  drawdown: DrawdownCurvePoint[];
  warnings: string[];
}

const toFiniteNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? value : 0;

export const normalizeDashboardStats = (
  stats: DashboardStats,
): NormalizedDashboardStats => ({
  total_balance: toFiniteNumber(stats.total_balance),
  current_equity: toFiniteNumber(stats.current_equity),
  max_drawdown: toFiniteNumber(stats.max_drawdown),
  win_rate: toFiniteNumber(stats.win_rate),
  total_trades: Math.trunc(toFiniteNumber(stats.total_trades)),
  monthly_pnl: toFiniteNumber(stats.monthly_pnl),
});

const normalizeEquityCurve = (points: EquityCurvePoint[] | null | undefined) =>
  (points ?? []).map((point) => ({
    ...point,
    equity: toFiniteNumber(point.equity),
    balance: toFiniteNumber(point.balance),
  }));

const normalizeDrawdownCurve = (
  points: DrawdownCurvePoint[] | null | undefined,
) =>
  (points ?? []).map((point) => ({
    ...point,
    drawdown: toFiniteNumber(point.drawdown),
  }));

export const shouldShowSignalCta = (stats: NormalizedDashboardStats) =>
  stats.total_trades === 0;

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
    stats: normalizeDashboardStats(statsResult.value.data),
    equity:
      equityResult.status === 'fulfilled'
        ? normalizeEquityCurve(equityResult.value.data)
        : [],
    drawdown:
      drawdownResult.status === 'fulfilled'
        ? normalizeDrawdownCurve(drawdownResult.value.data)
        : [],
    warnings,
  };
}

export function DashboardPage() {
  const [stats, setStats] = useState<NormalizedDashboardStats | null>(null);
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
      <ErrorState
        title="Unable to load dashboard"
        message={error ?? 'Dashboard stats were unavailable.'}
      />
    );
  }

  const showSignalCta = shouldShowSignalCta(stats);

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

      {showSignalCta && <DashboardOnboarding />}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <SessionControls />
        <LiveMarketWidget symbol="EURUSD" />
      </section>

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
            emptyMessage="No equity snapshots yet. Generate a signal, open a trade, and the metrics service will plot snapshots here."
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
            emptyMessage="No drawdown snapshots yet. Once trades or account snapshots exist, risk changes will appear here."
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

function DashboardOnboarding() {
  return (
    <section className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-6 text-blue-50 shadow-xl shadow-slate-950/20">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-200">
            New account next steps
          </p>
          <h3 className="mt-2 text-2xl font-bold text-white">
            Build your first dashboard curve
          </h3>
          <p className="mt-2 max-w-2xl text-sm text-blue-100/90">
            Configure strategy settings, generate a signal, then open a trade.
            The dashboard will stay at safe zero defaults until metrics arrive.
          </p>
        </div>
        <Link
          to="/signals"
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-blue-300"
        >
          Generate signal
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <OnboardingStep
          icon={<Settings className="h-4 w-4" />}
          title="1. Configure settings"
          description="Confirm symbols, timeframe, and risk before automation starts."
        />
        <OnboardingStep
          icon={<Sparkles className="h-4 w-4" />}
          title="2. Generate signal"
          description="Create a fresh strategy signal to validate the next action."
        />
        <OnboardingStep
          icon={<Activity className="h-4 w-4" />}
          title="3. Open trade"
          description="Use the signal to open a position and start collecting metrics."
        />
      </div>
    </section>
  );
}

interface OnboardingStepProps {
  icon: ReactNode;
  title: string;
  description: string;
}

function OnboardingStep({ icon, title, description }: OnboardingStepProps) {
  return (
    <div className="rounded-xl border border-blue-300/20 bg-slate-950/30 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-white">
        <span className="rounded-lg bg-blue-300/20 p-2 text-blue-100">
          {icon}
        </span>
        {title}
      </div>
      <p className="mt-3 text-sm text-blue-100/80">{description}</p>
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
