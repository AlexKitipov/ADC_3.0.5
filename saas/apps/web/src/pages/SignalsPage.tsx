import { useEffect, useState } from 'react';
import { signalsAPI } from '../api/signals';
import { LoadingState } from '../components/LoadingState';
import { Signal } from '../types';
import { formatCurrency, formatDateTime } from '../lib/format';

const actionClasses = {
  BUY: 'bg-emerald-500/10 text-emerald-300',
  SELL: 'bg-rose-500/10 text-rose-300',
  HOLD: 'bg-amber-500/10 text-amber-300',
};

export function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    signalsAPI
      .getLatest(25)
      .then((response) => setSignals(response.data))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading signals..." />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Signals</h2>
        <p className="mt-2 text-slate-400">Recent indicator-driven trading signals.</p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
        <table className="min-w-full divide-y divide-slate-800">
          <thead className="bg-slate-900">
            <tr>
              {['Symbol', 'Action', 'Price', 'RSI', 'MACD', 'Time'].map((header) => (
                <th key={header} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {signals.map((signal) => (
              <tr key={signal.id} className="hover:bg-slate-800/50">
                <td className="px-5 py-4 font-semibold text-white">{signal.symbol}</td>
                <td className="px-5 py-4">
                  <span className={`rounded-full px-3 py-1 text-xs font-bold ${actionClasses[signal.action]}`}>{signal.action}</span>
                </td>
                <td className="px-5 py-4 text-slate-300">{formatCurrency(signal.price)}</td>
                <td className="px-5 py-4 text-slate-300">{signal.rsi.toFixed(2)}</td>
                <td className="px-5 py-4 text-slate-300">{signal.macd.toFixed(4)}</td>
                <td className="px-5 py-4 text-slate-400">{formatDateTime(signal.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {signals.length === 0 && <p className="p-6 text-center text-slate-400">No signals yet.</p>}
      </div>
    </div>
  );
}
