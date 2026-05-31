import { useCallback, useEffect, useMemo, useState } from 'react';
import { signalsAPI } from '../api/signals';
import { LoadingState } from '../components/LoadingState';
import { EmptyState, ErrorState } from '../components/PageState';
import type { KnownSignalAction, Signal, SignalGenerateRequest } from '../types';
import { formatCurrency, formatDateTime } from '../lib/format';

const SIGNALS_LIMIT = 25;

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

export function describeRsi(rsi: number) {
  if (rsi >= 70) {
    return 'Overbought: RSI is above the 70 threshold, which can support sell or caution signals.';
  }
  if (rsi <= 30) {
    return 'Oversold: RSI is below the 30 threshold, which can support buy or rebound signals.';
  }
  return 'Neutral: RSI is between 30 and 70, so momentum is not at a common extreme.';
}

export function describeMacd(macd: number) {
  if (macd > 0) {
    return 'Bullish momentum: MACD is above zero, indicating short-term momentum is stronger than the slower trend.';
  }
  if (macd < 0) {
    return 'Bearish momentum: MACD is below zero, indicating short-term momentum is weaker than the slower trend.';
  }
  return 'Flat momentum: MACD is exactly zero, indicating no separation between the tracked moving averages.';
}

export function buildSignalExplanation(signal: Signal) {
  const explanation = [
    `${signal.action} signal for ${signal.symbol} at ${formatCurrency(signal.price)}.`,
    describeRsi(signal.rsi),
    describeMacd(signal.macd),
  ];

  if (signal.confidence !== undefined) {
    explanation.push(`Generator confidence: ${(signal.confidence * 100).toFixed(1)}%.`);
  }

  if (signal.explanation) {
    explanation.push(`Generator note: ${signal.explanation}`);
  }

  explanation.push(
    'These values are stored on the signal; the indicators API can recalculate a full stateless indicator set from submitted OHLCV rows for previews and diagnostics.',
  );

  return explanation;
}

export async function loadSignals(limit = SIGNALS_LIMIT) {
  try {
    const response = await signalsAPI.getLatest(limit);
    return response.data;
  } catch {
    throw new Error('Signals could not be loaded.');
  }
}

export async function generateSignal(payload?: SignalGenerateRequest) {
  try {
    const response = await signalsAPI.generate(payload);
    const { signal, decision } = response.data;
    return {
      ...signal,
      confidence: decision.confidence,
      explanation: decision.explanation,
    };
  } catch {
    throw new Error('Signal could not be generated.');
  }
}

export function mergeGeneratedSignal(signals: Signal[], generatedSignal: Signal) {
  return [
    generatedSignal,
    ...signals.filter((signal) => signal.id !== generatedSignal.id),
  ];
}

export function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [selectedSignalId, setSelectedSignalId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSignals = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const loadedSignals = await loadSignals();
      setSignals(loadedSignals);
      setSelectedSignalId((currentSelectedId) => {
        if (loadedSignals.some((signal) => signal.id === currentSelectedId)) {
          return currentSelectedId;
        }
        return loadedSignals[0]?.id ?? null;
      });
      setError(null);
      return loadedSignals;
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Signals could not be loaded.',
      );
      throw loadError;
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refreshSignals()
      .catch(() => {
        setSignals([]);
        setSelectedSignalId(null);
      })
      .finally(() => setIsLoading(false));
  }, [refreshSignals]);

  const handleRefresh = async () => {
    await refreshSignals().catch(() => undefined);
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const generatedSignal = await generateSignal();
      setSignals((currentSignals) => mergeGeneratedSignal(currentSignals, generatedSignal));
      setSelectedSignalId(generatedSignal.id);
      await refreshSignals().catch(() => undefined);
    } catch (generateError) {
      setError(
        generateError instanceof Error
          ? generateError.message
          : 'Signal could not be generated.',
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const selectedSignal = useMemo(
    () => signals.find((signal) => signal.id === selectedSignalId) ?? null,
    [selectedSignalId, signals],
  );

  if (isLoading) {
    return <LoadingState label="Loading signals..." />;
  }

  const isBusy = isRefreshing || isGenerating;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white">Signals</h2>
          <p className="mt-2 text-slate-400">Recent indicator-driven trading signals with explainable RSI and MACD context.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={handleRefresh}
            disabled={isBusy}
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button
            type="button"
            className="rounded-xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={handleGenerate}
            disabled={isBusy}
          >
            {isGenerating ? 'Generating...' : 'Generate signal'}
          </button>
        </div>
      </div>
      {error && <ErrorState title="Signals unavailable" message={error} />}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="bg-slate-900">
              <tr>
                {['Symbol', 'Action', 'Price', 'RSI', 'MACD', 'Time', 'Details'].map((header) => (
                  <th key={header} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {signals.map((signal) => {
                const isSelected = signal.id === selectedSignalId;
                return (
                  <tr key={signal.id} className={isSelected ? 'bg-slate-800/70' : 'hover:bg-slate-800/50'}>
                    <td className="px-5 py-4 font-semibold text-white">{signal.symbol}</td>
                    <td className="px-5 py-4">
                      <span className={`rounded-full px-3 py-1 text-xs font-bold ${getSignalActionClass(signal.action)}`}>{signal.action}</span>
                    </td>
                    <td className="px-5 py-4 text-slate-300">{formatCurrency(signal.price)}</td>
                    <td className="px-5 py-4 text-slate-300">{signal.rsi.toFixed(2)}</td>
                    <td className="px-5 py-4 text-slate-300">{signal.macd.toFixed(4)}</td>
                    <td className="px-5 py-4 text-slate-400">{formatDateTime(signal.timestamp)}</td>
                    <td className="px-5 py-4">
                      <button
                        type="button"
                        className="rounded-lg border border-cyan-500/40 px-3 py-1 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-500/10"
                        onClick={() => setSelectedSignalId(signal.id)}
                      >
                        Explain
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {signals.length === 0 && <EmptyState title="No signals yet" message="Signals will appear after the backend records indicator-driven decisions for configured symbols." />}
        </div>

        <aside className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-white">Signal explanation</h3>
              <p className="mt-1 text-sm text-slate-400">Stored signal values plus reusable indicator API context.</p>
            </div>
            <span className="rounded-full bg-cyan-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-cyan-200">Stateless</span>
          </div>

          {selectedSignal ? (
            <div className="mt-5 space-y-5">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl bg-slate-950/50 p-3">
                  <p className="text-slate-500">RSI</p>
                  <p className="mt-1 text-2xl font-bold text-white">{selectedSignal.rsi.toFixed(2)}</p>
                </div>
                <div className="rounded-xl bg-slate-950/50 p-3">
                  <p className="text-slate-500">MACD</p>
                  <p className="mt-1 text-2xl font-bold text-white">{selectedSignal.macd.toFixed(4)}</p>
                </div>
              </div>
              <ul className="space-y-3 text-sm text-slate-300">
                {buildSignalExplanation(selectedSignal).map((item) => (
                  <li key={item} className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">{item}</li>
                ))}
              </ul>
              <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-sm text-cyan-100">
                POST <code className="rounded bg-slate-950/70 px-1 py-0.5">/indicators/calculate</code> with OHLCV rows to preview RSI, MACD, Bollinger Bands, ATR, and pivot levels without creating a signal or simulation.
              </div>
            </div>
          ) : (
            <EmptyState title="Select a signal" message="Choose a signal row to inspect RSI, MACD, and stateless indicator context." />
          )}
        </aside>
      </div>
    </div>
  );
}
