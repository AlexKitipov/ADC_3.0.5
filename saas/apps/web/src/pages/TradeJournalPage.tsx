import { useEffect, useState } from 'react';
import { tradeJournalAPI } from '../api/tradeJournal';
import { EmptyState, ErrorState, StatusBanner } from '../components/PageState';
import { LoadingState } from '../components/LoadingState';
import type { TradeJournalSummary } from '../types';
import { formatCurrency } from '../lib/format';

export async function loadTradeJournal() {
  const response = await tradeJournalAPI.getJournal();
  return response.data;
}

export function TradeJournalPage() {
  const [journal, setJournal] = useState<TradeJournalSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTradeJournal()
      .then((data) => {
        setJournal(data);
        setError(null);
      })
      .catch((loadError) => {
        console.error('Failed to load trade journal:', loadError);
        setError('Trade journal artifacts could not be loaded.');
      })
      .finally(() => setIsLoading(false));
  }, []);

  const exportJournal = async () => {
    setIsExporting(true);
    setMessage(null);
    try {
      const response = await tradeJournalAPI.exportJournal();
      setMessage(`Export prepared: ${response.data.filename} (${response.data.artifact_count} artifacts).`);
    } catch (exportError) {
      console.error('Failed to export trade journal:', exportError);
      setError('Trade journal export could not be prepared.');
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return <LoadingState label="Loading trade journal..." />;
  }

  if (error && !journal) {
    return <ErrorState title="Journal unavailable" message={error} />;
  }

  const entries = journal?.entries ?? [];
  const artifacts = journal?.artifacts ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white">Advanced/Lab Trade Journal</h2>
          <p className="mt-2 text-slate-400">Advanced/Lab workspace to audit persisted trades, generated simulation artifacts, and import/export boundaries.</p>
        </div>
        <button type="button" onClick={exportJournal} disabled={isExporting} className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60">
          {isExporting ? 'Preparing export...' : 'Prepare export'}
        </button>
      </div>

      {message && <StatusBanner tone="success" message={message} />}
      {error && <StatusBanner tone="error" message={error} />}

      {journal && (
        <section className="grid gap-4 md:grid-cols-3">
          <Metric label="DB trades" value={journal.db_trade_count.toString()} description={`${journal.open_db_trade_count} open · ${journal.closed_db_trade_count} closed`} />
          <Metric label="Journal rows" value={entries.length.toString()} description={journal.relationships.persisted_trade_rows} />
          <Metric label="Artifacts" value={artifacts.filter((artifact) => artifact.exists).length.toString()} description={journal.relationships.journal_artifacts} />
        </section>
      )}

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="border-b border-slate-800 px-5 py-4"><h3 className="text-lg font-semibold text-white">Journal entries</h3></div>
          {entries.length > 0 ? (
            <table className="min-w-full divide-y divide-slate-800"><thead><tr>{['Row', 'Type', 'Entry', 'Exit', 'PnL'].map((header) => <th key={header} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">{header}</th>)}</tr></thead><tbody className="divide-y divide-slate-800">{entries.slice(0, 20).map((entry) => <tr key={entry.id}><td className="px-5 py-4 text-white">#{entry.row_number}</td><td className="px-5 py-4 text-slate-300">{entry.type ?? 'trade'}</td><td className="px-5 py-4 text-slate-300">{entry.entry_price === null ? '—' : formatCurrency(entry.entry_price)}</td><td className="px-5 py-4 text-slate-300">{entry.exit_price === null ? '—' : formatCurrency(entry.exit_price)}</td><td className="px-5 py-4 text-slate-300">{entry.pnl === null ? '—' : formatCurrency(entry.pnl)}</td></tr>)}</tbody></table>
          ) : <EmptyState title="No journal entries" message="Generate or import trade artifacts to populate journal rows." />}
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h3 className="text-lg font-semibold text-white">Managed artifacts</h3>
          {artifacts.length > 0 ? <ul className="mt-4 space-y-3">{artifacts.map((artifact) => <li key={artifact.name} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex items-center justify-between gap-3"><span className="font-semibold text-white">{artifact.name}</span><span className={artifact.exists ? 'text-emerald-300' : 'text-slate-500'}>{artifact.exists ? 'available' : 'missing'}</span></div><p className="mt-2 text-sm text-slate-400">{artifact.row_count ?? 0} rows · {artifact.size_bytes ?? 0} bytes · {artifact.content_type}</p></li>)}</ul> : <EmptyState title="No artifacts tracked" message="The journal endpoint returned no artifact metadata." />}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, description }: { label: string; value: string; description: string }) {
  return <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5"><p className="text-xs uppercase tracking-wider text-slate-500">{label}</p><p className="mt-2 text-3xl font-bold text-white">{value}</p><p className="mt-2 text-sm text-slate-400">{description}</p></div>;
}
