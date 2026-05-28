import { useEffect, useState } from 'react';
import { tradesAPI } from '../api/trades';
import { LoadingState } from '../components/LoadingState';
import { Trade } from '../types';
import { formatCurrency, formatDateTime, formatPercent } from '../lib/format';

export function TradesPage() {
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([tradesAPI.getOpen(), tradesAPI.getClosed()])
      .then(([openResponse, closedResponse]) => {
        setOpenTrades(openResponse.data);
        setClosedTrades(closedResponse.data);
      })
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading trades..." />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Trades</h2>
        <p className="mt-2 text-slate-400">Review open positions and closed trade performance.</p>
      </div>
      <TradeTable title="Open Trades" trades={openTrades} />
      <TradeTable title="Closed Trades" trades={closedTrades} showExit />
    </div>
  );
}

function TradeTable({ title, trades, showExit = false }: { title: string; trades: Trade[]; showExit?: boolean }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
      <div className="border-b border-slate-800 px-5 py-4">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      <table className="min-w-full divide-y divide-slate-800">
        <thead>
          <tr>
            {['Symbol', 'Entry', showExit ? 'Exit' : 'Status', 'PnL', 'Opened'].map((header) => (
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
            </tr>
          ))}
        </tbody>
      </table>
      {trades.length === 0 && <p className="p-6 text-center text-slate-400">No {title.toLowerCase()}.</p>}
    </section>
  );
}
