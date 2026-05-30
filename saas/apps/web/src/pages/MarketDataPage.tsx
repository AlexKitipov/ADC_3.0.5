import { FormEvent, useState } from 'react';
import { indicatorsAPI } from '../api/indicators';
import { marketDataAPI } from '../api/marketData';
import { EmptyState, ErrorState, StatusBanner } from '../components/PageState';
import type { IndicatorCalculationResponse, MarketDataResponse, MarketDataTimeframe } from '../types';
import { formatCurrency, formatDateTime } from '../lib/format';

const timeframes: MarketDataTimeframe[] = ['1d', '1min', '5min', '15min', '30min', '60min'];

export async function loadMarketData(symbol: string, timeframe: MarketDataTimeframe) {
  if (!symbol.trim()) {
    throw new Error('Symbol is required.');
  }
  const response = await marketDataAPI.getOHLCV({ symbol: symbol.trim().toUpperCase(), timeframe });
  return response.data;
}

export async function calculateIndicators(data: MarketDataResponse) {
  if (data.rows.length === 0) {
    throw new Error('No OHLCV rows are available for indicator calculation.');
  }
  const response = await indicatorsAPI.calculate({ rows: data.rows });
  return response.data;
}

export function MarketDataPage() {
  const [symbol, setSymbol] = useState('EURUSD');
  const [timeframe, setTimeframe] = useState<MarketDataTimeframe>('1d');
  const [data, setData] = useState<MarketDataResponse | null>(null);
  const [indicators, setIndicators] = useState<IndicatorCalculationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setIndicators(null);
    try {
      const nextData = await loadMarketData(symbol, timeframe);
      setData(nextData);
      if (nextData.rows.length > 0) {
        setIndicators(await calculateIndicators(nextData));
      }
    } catch (loadError) {
      console.error('Failed to load market data:', loadError);
      setData(null);
      setError(loadError instanceof Error ? loadError.message : 'Market data could not be loaded.');
    } finally {
      setIsLoading(false);
    }
  };

  const latestIndicator = indicators?.rows[indicators.rows.length - 1];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Advanced/Lab Market Data</h2>
        <p className="mt-2 text-slate-400">Advanced/Lab diagnostics for fetching backend OHLCV candles and running stateless indicators before signal or simulation work.</p>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 md:grid-cols-[1fr_12rem_auto]">
        <label className="text-sm font-medium text-slate-300">
          Symbol
          <input className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400" value={symbol} onChange={(event) => setSymbol(event.target.value)} />
        </label>
        <label className="text-sm font-medium text-slate-300">
          Timeframe
          <select className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400" value={timeframe} onChange={(event) => setTimeframe(event.target.value as MarketDataTimeframe)}>
            {timeframes.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </label>
        <button type="submit" disabled={isLoading} className="self-end rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60">
          {isLoading ? 'Loading...' : 'Load data'}
        </button>
      </form>

      {error && <ErrorState message={error} />}

      {data ? (
        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(22rem,0.8fr)]">
          <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
            <div className="border-b border-slate-800 px-5 py-4">
              <h3 className="text-lg font-semibold text-white">{data.symbol} candles</h3>
              <p className="mt-1 text-sm text-slate-400">{data.row_count} rows returned from /market-data/ohlcv.</p>
            </div>
            <table className="min-w-full divide-y divide-slate-800">
              <thead><tr>{['Time', 'Open', 'High', 'Low', 'Close', 'Volume'].map((header) => <th key={header} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">{header}</th>)}</tr></thead>
              <tbody className="divide-y divide-slate-800">
                {data.rows.slice(-12).reverse().map((row) => (
                  <tr key={`${row.timestamp}-${row.symbol}`}>
                    <td className="px-5 py-4 text-slate-400">{formatDateTime(row.timestamp)}</td>
                    <td className="px-5 py-4 text-slate-300">{formatCurrency(row.open)}</td>
                    <td className="px-5 py-4 text-slate-300">{formatCurrency(row.high)}</td>
                    <td className="px-5 py-4 text-slate-300">{formatCurrency(row.low)}</td>
                    <td className="px-5 py-4 font-semibold text-white">{formatCurrency(row.close)}</td>
                    <td className="px-5 py-4 text-slate-300">{row.volume.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.rows.length === 0 && <EmptyState title="No candles returned" message="The market data provider returned zero rows for this symbol/timeframe." />}
          </div>

          <aside className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <h3 className="text-lg font-semibold text-white">Indicator snapshot</h3>
            <p className="mt-1 text-sm text-slate-400">Calculated with /indicators/calculate from the returned OHLCV rows.</p>
            {latestIndicator ? (
              <div className="mt-5 grid gap-3">
                <Metric label="RSI" value={latestIndicator.indicators.rsi?.toFixed(2) ?? '—'} />
                <Metric label="MACD" value={latestIndicator.indicators.macd?.toFixed(4) ?? '—'} />
                <Metric label="ATR" value={latestIndicator.indicators.atr?.toFixed(4) ?? '—'} />
                <Metric label="Pivot" value={latestIndicator.indicators.pivot?.toFixed(4) ?? '—'} />
              </div>
            ) : (
              <StatusBanner tone="warning" message="Load market data with at least one row to calculate indicators." />
            )}
          </aside>
        </section>
      ) : !error && (
        <EmptyState title="No market data loaded" message="Choose a configured symbol and timeframe, then fetch candles from the backend market-data endpoint." />
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs uppercase tracking-wider text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold text-white">{value}</p></div>;
}
