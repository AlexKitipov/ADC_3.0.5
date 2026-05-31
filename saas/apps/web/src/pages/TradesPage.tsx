import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { tradesAPI } from '../api/trades';
import { LoadingState } from '../components/LoadingState';
import type { Trade } from '../types';
import { formatCurrency, formatDateTime, formatPercent } from '../lib/format';

interface TradesData {
  openTrades: Trade[];
  closedTrades: Trade[];
}

type TradeHistoryTab = 'open' | 'closed';

export async function loadTrades(): Promise<TradesData> {
  try {
    const [openResponse, closedResponse] = await Promise.all([
      tradesAPI.getOpen(),
      tradesAPI.getClosed(),
    ]);

    return {
      openTrades: openResponse.data,
      closedTrades: closedResponse.data,
    };
  } catch {
    throw new Error('Trade history could not be loaded.');
  }
}

export async function openSimpleTrade(symbol: string, entryPrice: number): Promise<Trade> {
  if (!symbol.trim()) {
    throw new Error('Symbol is required.');
  }
  if (!Number.isFinite(entryPrice) || entryPrice <= 0) {
    throw new Error('Entry price must be greater than zero.');
  }

  const response = await tradesAPI.openTrade({ symbol: symbol.trim().toUpperCase(), entry_price: entryPrice });
  return response.data;
}

export async function closeSimpleTrade(tradeId: number, exitPrice: number): Promise<Trade> {
  if (!Number.isFinite(exitPrice) || exitPrice <= 0) {
    throw new Error('Exit price must be greater than zero.');
  }

  const response = await tradesAPI.closeTrade(tradeId, { exit_price: exitPrice });
  return response.data;
}

function removeExitPrice(exitPrices: Record<number, string>, tradeId: number): Record<number, string> {
  return Object.fromEntries(Object.entries(exitPrices).filter(([currentTradeId]) => Number(currentTradeId) !== tradeId));
}

export function TradesPage() {
  const [activeTab, setActiveTab] = useState<TradeHistoryTab>('open');
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [symbol, setSymbol] = useState('');
  const [entryPrice, setEntryPrice] = useState('');
  const [exitPrices, setExitPrices] = useState<Record<number, string>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const refreshTrades = useCallback(
    () =>
      loadTrades()
        .then(({ openTrades: nextOpenTrades, closedTrades: nextClosedTrades }) => {
          setOpenTrades(nextOpenTrades);
          setClosedTrades(nextClosedTrades);
          setErrorMessage(null);
        })
        .catch((error: Error) => setErrorMessage(error.message))
        .finally(() => setIsLoading(false)),
    [],
  );

  useEffect(() => {
    refreshTrades();
  }, [refreshTrades]);

  const handleOpenTrade = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    openSimpleTrade(symbol, Number(entryPrice))
      .then((trade) => {
        setOpenTrades((currentTrades) => [trade, ...currentTrades]);
        setSymbol('');
        setEntryPrice('');
        setActiveTab('open');
        setSuccessMessage(`${trade.symbol} trade opened at ${formatCurrency(trade.entry_price)}.`);
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsSaving(false));
  };

  const handleCloseTrade = (tradeId: number) => {
    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    closeSimpleTrade(tradeId, Number(exitPrices[tradeId]))
      .then((trade) => {
        setOpenTrades((currentTrades) => currentTrades.filter((openTrade) => openTrade.id !== trade.id));
        setClosedTrades((currentTrades) => [trade, ...currentTrades]);
        setExitPrices((currentExitPrices) => removeExitPrice(currentExitPrices, tradeId));
        setActiveTab('closed');
        setSuccessMessage(`${trade.symbol} trade closed with ${formatTradePnl(trade)}.`);
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsSaving(false));
  };

  if (isLoading) {
    return <LoadingState label="Loading trades..." />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Trades</h2>
        <p className="mt-2 text-slate-400">
          Review the persisted MVP trade lifecycle. Opening and closing records uses the SaaS trade history API and does not submit broker orders.
        </p>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Open a mock trade</h3>
            <p className="mt-1 text-sm text-slate-400">
              Create a persisted trade-history row with a symbol and entry price, then close it from the Open tab with an exit price.
            </p>
          </div>
          <button
            className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-400 hover:text-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSaving}
            onClick={refreshTrades}
            type="button"
          >
            Refresh history
          </button>
        </div>
        <form className="mt-4 grid gap-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={handleOpenTrade}>
          <label className="text-sm font-medium text-slate-300">
            Symbol
            <input
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400"
              disabled={isSaving}
              onChange={(event) => setSymbol(event.target.value)}
              placeholder="BTCUSD"
              value={symbol}
            />
          </label>
          <label className="text-sm font-medium text-slate-300">
            Entry price
            <input
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400"
              disabled={isSaving}
              min="0"
              onChange={(event) => setEntryPrice(event.target.value)}
              placeholder="100.00"
              step="0.01"
              type="number"
              value={entryPrice}
            />
          </label>
          <button
            className="self-end rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSaving}
            type="submit"
          >
            Open trade
          </button>
        </form>
        {errorMessage && <p className="mt-4 text-sm text-rose-300">{errorMessage}</p>}
        {successMessage && <p className="mt-4 text-sm text-emerald-300">{successMessage}</p>}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
        <div className="flex flex-col gap-4 border-b border-slate-800 px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Trade history</h3>
            <p className="mt-1 text-sm text-slate-400">Open trades can be closed with an exit price; closed trades show realized PnL.</p>
          </div>
          <div className="flex rounded-xl border border-slate-800 bg-slate-950/70 p-1" role="tablist" aria-label="Trade history tabs">
            <TradeTabButton active={activeTab === 'open'} count={openTrades.length} label="Open" onClick={() => setActiveTab('open')} />
            <TradeTabButton active={activeTab === 'closed'} count={closedTrades.length} label="Closed" onClick={() => setActiveTab('closed')} />
          </div>
        </div>

        {activeTab === 'open' ? (
          <TradeTable
            emptyMessage="No open trades. Open a mock trade to start the lifecycle."
            exitPrices={exitPrices}
            isSaving={isSaving}
            onCloseTrade={handleCloseTrade}
            onExitPriceChange={(tradeId, exitPrice) => setExitPrices((currentExitPrices) => ({ ...currentExitPrices, [tradeId]: exitPrice }))}
            title="Open trades"
            trades={openTrades}
          />
        ) : (
          <TradeTable emptyMessage="No closed trades yet." showExit title="Closed trades" trades={closedTrades} />
        )}
      </section>
    </div>
  );
}

function TradeTabButton({ active, count, label, onClick }: { active: boolean; count: number; label: string; onClick: () => void }) {
  return (
    <button
      aria-selected={active}
      className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${active ? 'bg-cyan-500 text-slate-950' : 'text-slate-300 hover:text-white'}`}
      onClick={onClick}
      role="tab"
      type="button"
    >
      {label} <span className={active ? 'text-slate-800' : 'text-slate-500'}>({count})</span>
    </button>
  );
}

function formatTradePnl(trade: Trade): string {
  if (trade.pnl === null) {
    return 'unrealized PnL unavailable';
  }

  return `${formatCurrency(trade.pnl)} (${formatPercent((trade.pnl_percent ?? 0) / 100)})`;
}

function pnlClassName(trade: Trade): string {
  if (trade.pnl === null) {
    return 'text-slate-400';
  }

  return trade.pnl < 0 ? 'text-rose-300' : 'text-emerald-300';
}

function TradeTable({
  title,
  trades,
  showExit = false,
  emptyMessage,
  exitPrices = {},
  isSaving = false,
  onCloseTrade,
  onExitPriceChange,
}: {
  title: string;
  trades: Trade[];
  showExit?: boolean;
  emptyMessage: string;
  exitPrices?: Record<number, string>;
  isSaving?: boolean;
  onCloseTrade?: (tradeId: number) => void;
  onExitPriceChange?: (tradeId: number, exitPrice: string) => void;
}) {
  const headers = showExit ? ['Symbol', 'Entry', 'Exit', 'PnL', 'Opened', 'Closed'] : ['Symbol', 'Entry', 'Status', 'PnL', 'Opened', 'Close'];
  const tableDescriptionId = `${title.replace(/\s+/g, '-').toLowerCase()}-caption`;

  return (
    <div>
      <div className="sr-only" id={tableDescriptionId}>{title}</div>
      <table className="min-w-full divide-y divide-slate-800" aria-describedby={tableDescriptionId}>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {trades.map((trade) => (
            <tr key={trade.id}>
              <td className="px-5 py-4 font-semibold text-white">{trade.symbol}</td>
              <td className="px-5 py-4 text-slate-300">{formatCurrency(trade.entry_price)}</td>
              <td className="px-5 py-4 text-slate-300">{showExit ? (trade.exit_price ? formatCurrency(trade.exit_price) : '—') : trade.status}</td>
              <td className={`px-5 py-4 ${pnlClassName(trade)}`}>{formatTradePnl(trade)}</td>
              <td className="px-5 py-4 text-slate-400">{formatDateTime(trade.entry_time)}</td>
              {showExit ? (
                <td className="px-5 py-4 text-slate-400">{trade.exit_time ? formatDateTime(trade.exit_time) : '—'}</td>
              ) : (
                <td className="px-5 py-4">
                  <div className="flex gap-2">
                    <input
                      aria-label={`Exit price for ${trade.symbol}`}
                      className="w-28 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400"
                      disabled={isSaving}
                      min="0"
                      onChange={(event) => onExitPriceChange?.(trade.id, event.target.value)}
                      placeholder="Exit"
                      step="0.01"
                      type="number"
                      value={exitPrices[trade.id] ?? ''}
                    />
                    <button
                      className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-400 hover:text-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={isSaving}
                      onClick={() => onCloseTrade?.(trade.id)}
                      type="button"
                    >
                      Close trade
                    </button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {trades.length === 0 && <p className="p-6 text-center text-slate-400">{emptyMessage}</p>}
    </div>
  );
}
