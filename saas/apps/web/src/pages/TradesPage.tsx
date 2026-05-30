import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ordersAPI } from '../api/orders';
import { tradeJournalAPI } from '../api/tradeJournal';
import { tradesAPI } from '../api/trades';
import { LoadingState } from '../components/LoadingState';
import type { Order, OrderType, Trade, TradeJournalSummary } from '../types';
import { formatCurrency, formatDateTime, formatPercent } from '../lib/format';

interface TradesData {
  openTrades: Trade[];
  closedTrades: Trade[];
  openOrders: Order[];
  journal: TradeJournalSummary;
}

const ORDER_TYPES: OrderType[] = ['BUY', 'SELL', 'BUYSTOP', 'SELLSTOP', 'BUYLIMIT', 'SELLLIMIT'];

export async function loadTrades(): Promise<TradesData> {
  try {
    const [openResponse, closedResponse, ordersResponse, journalResponse] = await Promise.all([
      tradesAPI.getOpen(),
      tradesAPI.getClosed(),
      ordersAPI.getOpen(),
      tradeJournalAPI.getJournal(),
    ]);
    return { openTrades: openResponse.data, closedTrades: closedResponse.data, openOrders: ordersResponse.data, journal: journalResponse.data };
  } catch {
    throw new Error('Trades and manual orders could not be loaded.');
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

export async function submitManualOrder(
  symbol: string,
  orderType: OrderType,
  volume: number,
  price: number,
  stopLoss: number,
  takeProfit: number,
  slippage: number,
): Promise<Order> {
  if (!symbol.trim()) {
    throw new Error('Order symbol is required.');
  }
  if (!Number.isFinite(volume) || volume <= 0) {
    throw new Error('Order volume must be greater than zero.');
  }
  if (!Number.isFinite(price) || price <= 0) {
    throw new Error('Order price must be greater than zero.');
  }
  if (stopLoss < 0 || takeProfit < 0 || slippage < 0) {
    throw new Error('Stops and slippage cannot be negative.');
  }

  const response = await ordersAPI.createOrder({
    symbol: symbol.trim().toUpperCase(),
    order_type: orderType,
    volume,
    price,
    stop_loss: stopLoss || 0,
    take_profit: takeProfit || 0,
    slippage,
    comment: 'manual-order',
  });
  return response.data;
}

export async function closeManualOrder(ticket: number, price: number, slippage: number): Promise<Order> {
  if (!Number.isFinite(price) || price <= 0) {
    throw new Error('Close price must be greater than zero.');
  }
  if (slippage < 0) {
    throw new Error('Slippage cannot be negative.');
  }

  const response = await ordersAPI.closeOrder(ticket, { price, slippage, exit_reason: 'manual-close' });
  return response.data;
}

function removeExitPrice(exitPrices: Record<number, string>, tradeId: number): Record<number, string> {
  return Object.fromEntries(Object.entries(exitPrices).filter(([currentTradeId]) => Number(currentTradeId) !== tradeId));
}

export function TradesPage() {
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [openOrders, setOpenOrders] = useState<Order[]>([]);
  const [journal, setJournal] = useState<TradeJournalSummary | null>(null);
  const [isExportingJournal, setIsExportingJournal] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [symbol, setSymbol] = useState('');
  const [entryPrice, setEntryPrice] = useState('');
  const [exitPrices, setExitPrices] = useState<Record<number, string>>({});
  const [orderSymbol, setOrderSymbol] = useState('EURUSD');
  const [orderType, setOrderType] = useState<OrderType>('BUY');
  const [orderVolume, setOrderVolume] = useState('0.1');
  const [orderPrice, setOrderPrice] = useState('1.0851');
  const [orderStopLoss, setOrderStopLoss] = useState('');
  const [orderTakeProfit, setOrderTakeProfit] = useState('');
  const [orderSlippage, setOrderSlippage] = useState('100');
  const [orderClosePrices, setOrderClosePrices] = useState<Record<number, string>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [orderMessage, setOrderMessage] = useState<string | null>(null);

  const refreshTrades = useCallback(
    () =>
      loadTrades()
        .then(({ openTrades: nextOpenTrades, closedTrades: nextClosedTrades, openOrders: nextOpenOrders, journal: nextJournal }) => {
          setOpenTrades(nextOpenTrades);
          setClosedTrades(nextClosedTrades);
          setOpenOrders(nextOpenOrders);
          setJournal(nextJournal);
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

    openSimpleTrade(symbol, Number(entryPrice))
      .then((trade) => {
        setOpenTrades((currentTrades) => [trade, ...currentTrades]);
        setSymbol('');
        setEntryPrice('');
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsSaving(false));
  };

  const handleCloseTrade = (tradeId: number) => {
    setIsSaving(true);
    setErrorMessage(null);

    closeSimpleTrade(tradeId, Number(exitPrices[tradeId]))
      .then((trade) => {
        setOpenTrades((currentTrades) => currentTrades.filter((openTrade) => openTrade.id !== trade.id));
        setClosedTrades((currentTrades) => [trade, ...currentTrades]);
        setExitPrices((currentExitPrices) => removeExitPrice(currentExitPrices, tradeId));
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsSaving(false));
  };

  const handleSubmitManualOrder = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setOrderMessage(null);

    submitManualOrder(
      orderSymbol,
      orderType,
      Number(orderVolume),
      Number(orderPrice),
      Number(orderStopLoss || 0),
      Number(orderTakeProfit || 0),
      Number(orderSlippage || 0),
    )
      .then((order) => {
        setOpenOrders((currentOrders) => [order, ...currentOrders]);
        setOrderMessage(order.broker_result.message);
      })
      .catch((error: Error) => setOrderMessage(error.message))
      .finally(() => setIsSaving(false));
  };

  const handleExportJournal = () => {
    setIsExportingJournal(true);
    setErrorMessage(null);

    tradeJournalAPI.exportJournal()
      .then((response) => setErrorMessage(`Journal archive ready: ${response.data.filename} (${response.data.artifact_count} artifacts).`))
      .catch(() => setErrorMessage('Trade journal export could not be prepared.'))
      .finally(() => setIsExportingJournal(false));
  };

  const handleCloseManualOrder = (ticket: number) => {
    setIsSaving(true);
    setOrderMessage(null);

    closeManualOrder(ticket, Number(orderClosePrices[ticket]), Number(orderSlippage || 0))
      .then((order) => {
        setOpenOrders((currentOrders) => currentOrders.filter((openOrder) => openOrder.ticket !== order.ticket));
        setOrderClosePrices((currentPrices) => removeExitPrice(currentPrices, ticket));
        setOrderMessage(order.broker_result.message);
      })
      .catch((error: Error) => setOrderMessage(error.message))
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
          Review persisted trade journal rows separately from manual mock-broker orders. Manual order actions submit to the order-management layer and do not create Trade records.
        </p>
      </div>

      <section className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-5">
        <h3 className="text-lg font-semibold text-amber-100">Manual broker order</h3>
        <p className="mt-1 text-sm text-amber-100/80">
          Risk-sensitive controls route to the mock broker. Confirm symbol, side, volume, price, stops, and slippage before submitting.
        </p>
        <form className="mt-4 grid gap-4 lg:grid-cols-7" onSubmit={handleSubmitManualOrder}>
          <label className="text-sm font-medium text-slate-300">
            Symbol
            <input className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-300" disabled={isSaving} onChange={(event) => setOrderSymbol(event.target.value)} value={orderSymbol} />
          </label>
          <label className="text-sm font-medium text-slate-300">
            Type
            <select className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-300" disabled={isSaving} onChange={(event) => setOrderType(event.target.value as OrderType)} value={orderType}>
              {ORDER_TYPES.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </label>
          <NumberField disabled={isSaving} label="Volume" onChange={setOrderVolume} step="0.01" value={orderVolume} />
          <NumberField disabled={isSaving} label="Price" onChange={setOrderPrice} step="0.00001" value={orderPrice} />
          <NumberField disabled={isSaving} label="Stop loss" onChange={setOrderStopLoss} placeholder="Optional" step="0.00001" value={orderStopLoss} />
          <NumberField disabled={isSaving} label="Take profit" onChange={setOrderTakeProfit} placeholder="Optional" step="0.00001" value={orderTakeProfit} />
          <NumberField disabled={isSaving} label="Slippage" onChange={setOrderSlippage} step="1" value={orderSlippage} />
          <button className="rounded-lg bg-amber-300 px-4 py-2 font-semibold text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-60 lg:col-span-7" disabled={isSaving} type="submit">
            Submit manual order
          </button>
        </form>
        {orderMessage && <p className="mt-4 text-sm text-amber-100">{orderMessage}</p>}
      </section>

      <OrderTable
        closePrices={orderClosePrices}
        isSaving={isSaving}
        onCloseOrder={handleCloseManualOrder}
        onClosePriceChange={(ticket, price) => setOrderClosePrices((currentPrices) => ({ ...currentPrices, [ticket]: price }))}
        orders={openOrders}
      />

      {journal && <JournalArchivePanel isExporting={isExportingJournal} journal={journal} onExport={handleExportJournal} />}

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <h3 className="text-lg font-semibold text-white">Open a simple trade record</h3>
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
            Open record
          </button>
        </form>
        {errorMessage && <p className="mt-4 text-sm text-rose-300">{errorMessage}</p>}
      </section>

      <TradeTable
        exitPrices={exitPrices}
        isSaving={isSaving}
        onCloseTrade={handleCloseTrade}
        onExitPriceChange={(tradeId, exitPrice) => setExitPrices((currentExitPrices) => ({ ...currentExitPrices, [tradeId]: exitPrice }))}
        title="Open Trades"
        trades={openTrades}
      />
      <TradeTable title="Closed Trades" trades={closedTrades} showExit />
    </div>
  );
}

function JournalArchivePanel({
  isExporting,
  journal,
  onExport,
}: {
  isExporting: boolean;
  journal: TradeJournalSummary;
  onExport: () => void;
}) {
  const existingArtifacts = journal.artifacts.filter((artifact) => artifact.exists);
  const latestEntries = journal.entries.slice(0, 3);

  return (
    <section className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-cyan-100">Journal archive</h3>
          <p className="mt-1 text-sm text-cyan-100/80">
            Browse simulation CSV/JSON artifacts separately from database trades and broker orders.
          </p>
        </div>
        <button
          className="rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isExporting}
          onClick={onExport}
          type="button"
        >
          {isExporting ? 'Preparing export...' : 'Prepare export'}
        </button>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <BoundaryCard label="Persisted Trade DB rows" value={`${journal.db_trade_count} total`} description={journal.relationships.persisted_trade_rows} />
        <BoundaryCard label="Broker/order records" value="Order layer" description={journal.relationships.broker_order_records} />
        <BoundaryCard label="CSV/JSON artifacts" value={`${existingArtifacts.length} files`} description={journal.relationships.journal_artifacts} />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div className="rounded-xl border border-cyan-400/20 bg-slate-950/40 p-4">
          <h4 className="font-semibold text-white">Managed artifacts</h4>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            {journal.artifacts.map((artifact) => (
              <li key={artifact.name} className="flex items-center justify-between gap-3 rounded-lg bg-slate-950/50 px-3 py-2">
                <span className="font-medium text-slate-100">{artifact.name}</span>
                <span className={artifact.exists ? 'text-emerald-300' : 'text-slate-500'}>
                  {artifact.exists ? `${artifact.row_count ?? 0} rows · ${artifact.size_bytes ?? 0} bytes` : 'not found'}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-cyan-400/20 bg-slate-950/40 p-4">
          <h4 className="font-semibold text-white">Latest journal entries</h4>
          {latestEntries.length > 0 ? (
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              {latestEntries.map((entry) => (
                <li key={entry.id} className="rounded-lg bg-slate-950/50 px-3 py-2">
                  <span className="font-semibold text-slate-100">#{entry.row_number} {entry.type ?? 'trade'}</span>
                  <span className="ml-2 text-slate-400">PnL {entry.pnl === null ? '—' : formatCurrency(entry.pnl)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-400">No trade journal CSV rows have been imported or generated yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function BoundaryCard({ label, value, description }: { label: string; value: string; description: string }) {
  return (
    <div className="rounded-xl border border-cyan-400/20 bg-slate-950/40 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-cyan-200/80">{label}</p>
      <p className="mt-2 text-2xl font-bold text-white">{value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-300">{description}</p>
    </div>
  );
}


function NumberField({ disabled, label, onChange, placeholder, step, value }: { disabled: boolean; label: string; onChange: (value: string) => void; placeholder?: string; step: string; value: string }) {
  return (
    <label className="text-sm font-medium text-slate-300">
      {label}
      <input className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-300" disabled={disabled} min="0" onChange={(event) => onChange(event.target.value)} placeholder={placeholder} step={step} type="number" value={value} />
    </label>
  );
}

function OrderTable({ closePrices, isSaving, onCloseOrder, onClosePriceChange, orders }: { closePrices: Record<number, string>; isSaving: boolean; onCloseOrder: (ticket: number) => void; onClosePriceChange: (ticket: number, price: string) => void; orders: Order[] }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
      <div className="border-b border-slate-800 px-5 py-4">
        <h3 className="text-lg font-semibold text-white">Open Manual Orders</h3>
        <p className="mt-1 text-sm text-slate-400">Mock-broker orders are session-scoped and separate from persisted trade journal rows.</p>
      </div>
      <table className="min-w-full divide-y divide-slate-800">
        <thead>
          <tr>
            {['Ticket', 'Symbol', 'Type', 'Volume', 'Open price', 'SL / TP', 'Opened', 'Close'].map((header) => (
              <th key={header} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {orders.map((order) => (
            <tr key={order.ticket}>
              <td className="px-5 py-4 font-semibold text-white">{order.ticket}</td>
              <td className="px-5 py-4 text-slate-300">{order.symbol}</td>
              <td className="px-5 py-4 text-slate-300">{order.order_type}</td>
              <td className="px-5 py-4 text-slate-300">{order.volume}</td>
              <td className="px-5 py-4 text-slate-300">{formatCurrency(order.price)}</td>
              <td className="px-5 py-4 text-slate-300">{order.stop_loss || '—'} / {order.take_profit || '—'}</td>
              <td className="px-5 py-4 text-slate-400">{formatDateTime(order.open_time)}</td>
              <td className="px-5 py-4">
                <div className="flex gap-2">
                  <input aria-label={`Close price for order ${order.ticket}`} className="w-28 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-300" disabled={isSaving} min="0" onChange={(event) => onClosePriceChange(order.ticket, event.target.value)} placeholder="Close" step="0.00001" type="number" value={closePrices[order.ticket] ?? ''} />
                  <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:border-amber-300 hover:text-amber-100 disabled:cursor-not-allowed disabled:opacity-60" disabled={isSaving} onClick={() => onCloseOrder(order.ticket)} type="button">Close order</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {orders.length === 0 && <p className="p-6 text-center text-slate-400">No open manual orders.</p>}
    </section>
  );
}

function TradeTable({
  title,
  trades,
  showExit = false,
  exitPrices = {},
  isSaving = false,
  onCloseTrade,
  onExitPriceChange,
}: {
  title: string;
  trades: Trade[];
  showExit?: boolean;
  exitPrices?: Record<number, string>;
  isSaving?: boolean;
  onCloseTrade?: (tradeId: number) => void;
  onExitPriceChange?: (tradeId: number, exitPrice: string) => void;
}) {
  const headers = showExit ? ['Symbol', 'Entry', 'Exit', 'PnL', 'Opened'] : ['Symbol', 'Entry', 'Status', 'PnL', 'Opened', 'Close'];

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
      <div className="border-b border-slate-800 px-5 py-4">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      <table className="min-w-full divide-y divide-slate-800">
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
              <td className="px-5 py-4 text-slate-300">{showExit && trade.exit_price ? formatCurrency(trade.exit_price) : trade.status}</td>
              <td className={`px-5 py-4 ${trade.pnl && trade.pnl < 0 ? 'text-rose-300' : 'text-emerald-300'}`}>
                {trade.pnl === null ? '—' : `${formatCurrency(trade.pnl)} (${formatPercent((trade.pnl_percent ?? 0) / 100)})`}
              </td>
              <td className="px-5 py-4 text-slate-400">{formatDateTime(trade.entry_time)}</td>
              {!showExit && (
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
                      className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-400 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={isSaving}
                      onClick={() => onCloseTrade?.(trade.id)}
                      type="button"
                    >
                      Close
                    </button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {trades.length === 0 && <p className="p-6 text-center text-slate-400">No {title.toLowerCase()}.</p>}
    </section>
  );
}
