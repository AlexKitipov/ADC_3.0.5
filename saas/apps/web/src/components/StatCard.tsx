import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  tone?: 'blue' | 'green' | 'red' | 'amber';
}

const toneClasses = {
  blue: 'bg-blue-500/10 text-blue-300',
  green: 'bg-emerald-500/10 text-emerald-300',
  red: 'bg-rose-500/10 text-rose-300',
  amber: 'bg-amber-500/10 text-amber-300',
};

export function StatCard({ label, value, icon: Icon, tone = 'blue' }: StatCardProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl shadow-slate-950/20">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">{label}</p>
        <span className={`rounded-lg p-2 ${toneClasses[tone]}`}>
          <Icon size={18} />
        </span>
      </div>
      <p className="mt-4 text-2xl font-bold text-white">{value}</p>
    </div>
  );
}
