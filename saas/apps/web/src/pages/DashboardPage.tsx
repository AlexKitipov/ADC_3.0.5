import { useEffect, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, DollarSign, Percent, ShieldAlert, TrendingUp, Trophy } from 'lucide-react';
import { dashboardAPI } from '../api/dashboard';
import { LoadingState } from '../components/LoadingState';
import { StatCard } from '../components/StatCard';
import { DashboardStats, EquityPoint } from '../types';
import { formatCurrency, formatPercent } from '../lib/format';

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [equity, setEquity] = useState<EquityPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([dashboardAPI.getStats(), dashboardAPI.getEquityCurve()])
      .then(([statsResponse, equityResponse]) => {
        setStats(statsResponse.data);
        setEquity(equityResponse.data);
      })
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading || !stats) {
    return <LoadingState label="Loading dashboard..." />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Dashboard</h2>
        <p className="mt-2 text-slate-400">Monitor account equity, drawdown, and trading outcomes.</p>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatCard label="Total Balance" value={formatCurrency(stats.total_balance)} icon={DollarSign} />
        <StatCard label="Current Equity" value={formatCurrency(stats.current_equity)} icon={TrendingUp} tone="green" />
        <StatCard label="Max Drawdown" value={formatPercent(stats.max_drawdown)} icon={ShieldAlert} tone="red" />
        <StatCard label="Win Rate" value={formatPercent(stats.win_rate)} icon={Trophy} tone="amber" />
        <StatCard label="Total Trades" value={stats.total_trades.toString()} icon={Activity} />
        <StatCard label="Monthly PnL" value={formatCurrency(stats.monthly_pnl)} icon={Percent} tone={stats.monthly_pnl >= 0 ? 'green' : 'red'} />
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="mb-6">
          <h3 className="text-xl font-semibold text-white">Equity Curve</h3>
          <p className="text-sm text-slate-400">Last 30 days of balance and equity snapshots.</p>
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
              <XAxis dataKey="timestamp" tickFormatter={(value) => new Date(value).toLocaleDateString()} stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px' }} />
              <Area type="monotone" dataKey="equity" stroke="#60a5fa" fill="url(#equity)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
