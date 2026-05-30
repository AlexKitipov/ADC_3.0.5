import { AlertTriangle, Inbox, RefreshCw, Settings } from 'lucide-react';
import { Link } from 'react-router-dom';

interface ErrorStateProps {
  title?: string;
  message: string;
  actionLabel?: string;
  onRetry?: () => void;
}

export function ErrorState({ title = 'Unable to load data', message, actionLabel = 'Retry', onRetry }: ErrorStateProps) {
  return (
    <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-100" role="alert">
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-6 w-6 text-rose-300" />
        <h2 className="text-xl font-semibold">{title}</h2>
      </div>
      <p className="mt-3 text-sm text-rose-200">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-rose-300/40 px-3 py-2 text-sm font-semibold text-rose-50 hover:bg-rose-400/10"
        >
          <RefreshCw size={15} />
          {actionLabel}
        </button>
      )}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  message: string;
  actionLabel?: string;
  actionTo?: string;
}

export function EmptyState({ title, message, actionLabel, actionTo }: EmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/40 p-6 text-center">
      <Inbox className="mx-auto h-8 w-8 text-slate-500" />
      <h3 className="mt-3 text-lg font-semibold text-white">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-400">{message}</p>
      {actionLabel && actionTo && (
        <Link
          to={actionTo}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-brand-500/40 px-3 py-2 text-sm font-semibold text-brand-200 hover:bg-brand-500/10"
        >
          <Settings size={15} />
          {actionLabel}
        </Link>
      )}
    </div>
  );
}

interface StatusBannerProps {
  tone?: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

const toneClasses = {
  info: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-100',
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100',
  warning: 'border-amber-500/30 bg-amber-500/10 text-amber-100',
  error: 'border-rose-500/30 bg-rose-500/10 text-rose-100',
};

export function StatusBanner({ tone = 'info', message }: StatusBannerProps) {
  return (
    <div className={`rounded-2xl border p-4 text-sm ${toneClasses[tone]}`}>
      {message}
    </div>
  );
}
