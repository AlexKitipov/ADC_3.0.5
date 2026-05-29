import { useEffect, useState } from 'react';
import { signalsAPI } from '../api/signals';
import { LoadingState } from '../components/LoadingState';
import type { KnownSignalAction, Signal } from '../types';
import { formatCurrency, formatDateTime } from '../lib/format';

const actionClasses: Record<KnownSignalAction, string> = {
  BUY: 'bg-emerald-500/10 text-emerald-300',
  SELL: 'bg-rose-500/10 text-rose-300',
  HOLD: 'bg-amber-500/10 text-amber-300',
};

const unknownActionClass = 'bg-slate-500/10 text-slate-300';

export function getSignalActionClass(action: Signal['action']) {
  return Object.prototype.hasOwnProperty.call(actionClasses, action)
    ? actionClasses[action as KnownSignalAction]
    : unknownActionClass;
}

export async function loadSignals(limit = 25) {
  try {
    const response = await signalsAPI.getLatest(limit);
    return response.data;
  } catch {
    throw new Error('Signals could not be loaded.');
  }
}

export function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSignals()
      .then((loadedSignals) => {
        setSignals(loadedSignals);
        setError(null);
      })
      .catch((loadError) => {
        setSignals([]);
        setError(
          loadError instanceof Error
            ? loadError.message
            : 'Signals could not be loaded.',
        );
      })
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
      {error && (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200" role="alert">
          {error}
        </div>
      )}
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
                  <span className={`rounded-full px-3 py-1 text-xs font-bold ${getSignalActionClass(signal.action)}`}>{signal.action}</span>
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
