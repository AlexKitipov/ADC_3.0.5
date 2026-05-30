import { Radio, WifiOff } from 'lucide-react';
import { useMarketStream } from '../hooks/useMarketStream';
import { formatCurrency } from '../lib/format';

interface LiveMarketWidgetProps {
  compact?: boolean;
  symbol?: string;
}

export function LiveMarketWidget({ compact = false, symbol = 'EURUSD' }: LiveMarketWidgetProps) {
  const { latestTick, ticks, status, error } = useMarketStream(symbol, {
    interval: 1,
  });
  const previousTick = ticks[1];
  const priceDelta = latestTick && previousTick
    ? latestTick.price - previousTick.price
    : 0;
  const isUp = priceDelta >= 0;

  if (compact) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3 shadow-xl shadow-slate-950/20" aria-label="Live market stream status">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-300">Stream</p>
            <p className="mt-1 font-semibold text-white">{symbol.toUpperCase()} · {latestTick ? formatCurrency(latestTick.price) : 'Waiting'}</p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
            {status === 'reconnecting' ? <WifiOff className="h-4 w-4 text-amber-300" /> : <Radio className="h-4 w-4 text-emerald-300" />}
            {status}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl shadow-slate-950/40">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-cyan-300">
            Live Market
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-white">
            {symbol.toUpperCase()}
          </h3>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
          {status === 'reconnecting' ? (
            <WifiOff className="h-4 w-4 text-amber-300" />
          ) : (
            <Radio className="h-4 w-4 text-emerald-300" />
          )}
          {status}
        </div>
      </div>

      <div className="mt-6">
        <p className="text-sm text-slate-400">Mid price</p>
        <p className="mt-1 text-4xl font-bold text-white">
          {latestTick ? formatCurrency(latestTick.price) : 'Waiting...'}
        </p>
        {latestTick && (
          <p
            className={
              isUp
                ? 'mt-2 text-sm text-emerald-300'
                : 'mt-2 text-sm text-rose-300'
            }
          >
            {isUp ? '+' : ''}
            {priceDelta.toFixed(5)} since last tick
          </p>
        )}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3">
        <Quote label="Bid" value={latestTick?.bid} />
        <Quote label="Ask" value={latestTick?.ask} />
      </div>

      {latestTick && (
        <p className="mt-4 text-xs text-slate-500">
          Last update {new Date(latestTick.timestamp).toLocaleTimeString()}
        </p>
      )}
      {error && <p className="mt-4 text-sm text-amber-200">{error}</p>}
    </section>
  );
}

interface QuoteProps {
  label: string;
  value?: number;
}

function Quote({ label, value }: QuoteProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold text-slate-100">
        {value === undefined ? '—' : formatCurrency(value)}
      </p>
    </div>
  );
}
