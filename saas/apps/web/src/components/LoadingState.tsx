export function LoadingState({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="flex min-h-64 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/60 text-slate-300">
      {label}
    </div>
  );
}
