import { FormEvent, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileText, Loader2, Play, XCircle } from 'lucide-react';
import { simulationsAPI } from '../api/simulations';
import type { SimulationArtifact, SimulationRequest, SimulationRun } from '../types';

const defaultForm: Required<Pick<
  SimulationRequest,
  | 'symbol'
  | 'timeframe'
  | 'output_dir'
  | 'rl_algorithm'
  | 'rl_total_timesteps'
  | 'initial_balance'
  | 'grid_levels'
  | 'grid_step_pct'
  | 'martingale_factor'
  | 'train_lstm'
  | 'train_rl'
  | 'save_charts'
>> & Pick<SimulationRequest, 'start_date' | 'end_date' | 'generated_steps' | 'random_seed'> = {
  symbol: 'TSLA',
  timeframe: '1d',
  start_date: '',
  end_date: '',
  output_dir: 'simulation_output',
  generated_steps: 50,
  rl_algorithm: 'PPO',
  rl_total_timesteps: 1000,
  initial_balance: 10000,
  grid_levels: 3,
  grid_step_pct: 0.005,
  martingale_factor: 1.1,
  random_seed: 42,
  train_lstm: false,
  train_rl: false,
  save_charts: true,
};

export function SimulationPage() {
  const [form, setForm] = useState(defaultForm);
  const [simulation, setSimulation] = useState<SimulationRun | null>(null);
  const [artifacts, setArtifacts] = useState<SimulationArtifact[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingArtifacts, setIsLoadingArtifacts] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateForm = <K extends keyof typeof defaultForm>(key: K, value: (typeof defaultForm)[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setArtifacts([]);

    const payload: SimulationRequest = {
      ...form,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      generated_steps: form.generated_steps || null,
      random_seed: form.random_seed ?? null,
    };

    try {
      const response = await simulationsAPI.create(payload);
      setSimulation(response.data);
      if (response.data.status === 'completed') {
        await loadArtifacts(response.data.id);
      }
    } catch (submitError) {
      console.error('Failed to start simulation:', submitError);
      setError('Failed to start simulation. Check the parameters and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const refreshSimulation = async () => {
    if (!simulation) {
      return;
    }
    try {
      const response = await simulationsAPI.get(simulation.id);
      setSimulation(response.data);
      if (response.data.status === 'completed') {
        await loadArtifacts(response.data.id);
      }
    } catch (refreshError) {
      console.error('Failed to refresh simulation:', refreshError);
      setError('Failed to refresh simulation status.');
    }
  };

  const loadArtifacts = async (simulationId: string) => {
    setIsLoadingArtifacts(true);
    try {
      const response = await simulationsAPI.getArtifacts(simulationId);
      setArtifacts(response.data);
    } catch (artifactError) {
      console.error('Failed to load artifacts:', artifactError);
      setArtifacts([]);
    } finally {
      setIsLoadingArtifacts(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">Simulations</h2>
        <p className="mt-2 text-slate-400">
          Start backend ADC pivot-grid simulations and inspect the generated reports, charts, and datasets.
        </p>
      </div>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.9fr)]">
        <form onSubmit={handleSubmit} className="space-y-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div>
            <h3 className="text-xl font-semibold text-white">Simulation request</h3>
            <p className="mt-1 text-sm text-slate-400">
              Defaults are smoke-test friendly. Enable LSTM/RL training for full production experiments.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <TextField label="Symbol" value={form.symbol} onChange={(value) => updateForm('symbol', value)} />
            <SelectField
              label="Timeframe"
              value={form.timeframe}
              options={['1d', '5min', '15min', '30min', '60min']}
              onChange={(value) => updateForm('timeframe', value)}
            />
            <TextField label="Start date" type="date" value={form.start_date ?? ''} onChange={(value) => updateForm('start_date', value)} />
            <TextField label="End date" type="date" value={form.end_date ?? ''} onChange={(value) => updateForm('end_date', value)} />
            <TextField label="Output directory" value={form.output_dir} onChange={(value) => updateForm('output_dir', value)} />
            <NumberField label="Generated steps" value={form.generated_steps ?? 0} onChange={(value) => updateForm('generated_steps', value)} />
            <SelectField
              label="RL algorithm"
              value={form.rl_algorithm}
              options={['PPO', 'DQN', 'A2C', 'SAC']}
              onChange={(value) => updateForm('rl_algorithm', value)}
            />
            <NumberField label="RL timesteps" value={form.rl_total_timesteps} onChange={(value) => updateForm('rl_total_timesteps', value)} />
            <NumberField label="Initial balance" value={form.initial_balance} onChange={(value) => updateForm('initial_balance', value)} />
            <NumberField label="Grid levels" value={form.grid_levels} onChange={(value) => updateForm('grid_levels', value)} />
            <NumberField label="Grid step %" step="0.001" value={form.grid_step_pct} onChange={(value) => updateForm('grid_step_pct', value)} />
            <NumberField label="Martingale factor" step="0.1" value={form.martingale_factor} onChange={(value) => updateForm('martingale_factor', value)} />
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Toggle label="Train LSTM" checked={form.train_lstm} onChange={(value) => updateForm('train_lstm', value)} />
            <Toggle label="Train RL" checked={form.train_rl} onChange={(value) => updateForm('train_rl', value)} />
            <Toggle label="Save charts" checked={form.save_charts} onChange={(value) => updateForm('save_charts', value)} />
          </div>

          {error && <StatusBanner tone="error" message={error} />}

          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Play className="h-5 w-5" />}
            {isSubmitting ? 'Running simulation...' : 'Start simulation'}
          </button>
        </form>

        <aside className="space-y-6">
          <ResultSummary simulation={simulation} onRefresh={refreshSimulation} />
          <ArtifactList artifacts={artifacts} isLoading={isLoadingArtifacts} />
        </aside>
      </section>
    </div>
  );
}

function ResultSummary({ simulation, onRefresh }: { simulation: SimulationRun | null; onRefresh: () => void }) {
  if (!simulation) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-slate-400">
        Run a simulation to view status, performance metrics, and artifact outputs.
      </div>
    );
  }

  const statusTone = simulation.status === 'completed' ? 'success' : simulation.status === 'failed' ? 'error' : 'warning';
  const result = simulation.result;

  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-semibold text-white">Latest run</h3>
          <p className="mt-1 break-all text-xs text-slate-500">ID: {simulation.id}</p>
        </div>
        <button type="button" onClick={onRefresh} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800">
          Refresh
        </button>
      </div>

      <StatusBanner tone={statusTone} message={`Status: ${simulation.status}`} />
      {simulation.error && <StatusBanner tone="error" message={simulation.error} />}

      {result && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Metric label="Total steps" value={result.total_steps.toString()} />
          <Metric label="Trained LSTM" value={result.trained_lstm ? 'Yes' : 'No'} />
          <Metric label="Trained RL" value={result.trained_rl ? 'Yes' : 'No'} />
          <Metric label="Output" value={result.output_dir} />
          {Object.entries(result.performance).slice(0, 6).map(([key, value]) => (
            <Metric key={key} label={key.replaceAll('_', ' ')} value={String(value)} />
          ))}
        </div>
      )}
    </div>
  );
}

function ArtifactList({ artifacts, isLoading }: { artifacts: SimulationArtifact[]; isLoading: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
      <h3 className="text-xl font-semibold text-white">Artifacts</h3>
      {isLoading && <p className="mt-3 text-sm text-slate-400">Loading artifacts...</p>}
      {!isLoading && artifacts.length === 0 && <p className="mt-3 text-sm text-slate-400">No artifacts available yet.</p>}
      <div className="mt-4 space-y-3">
        {artifacts.map((artifact) => (
          <div key={artifact.name} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="flex items-center gap-2 text-sm font-medium text-white">
              <FileText className="h-4 w-4 text-brand-300" />
              {artifact.name.replaceAll('_', ' ')}
            </div>
            <p className="mt-1 break-all text-xs text-slate-500">{artifact.path}</p>
            <p className={artifact.exists ? 'mt-2 text-xs text-emerald-300' : 'mt-2 text-xs text-amber-300'}>
              {artifact.exists ? `${artifact.size_bytes ?? 0} bytes` : 'File not found on disk'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function TextField({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="block">
      <span className="text-sm text-slate-300">{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500" />
    </label>
  );
}

function NumberField({ label, value, onChange, step = '1' }: { label: string; value: number; onChange: (value: number) => void; step?: string }) {
  return (
    <label className="block">
      <span className="text-sm text-slate-300">{label}</span>
      <input type="number" step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500" />
    </label>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="text-sm text-slate-300">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500">
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
      {label}
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-5 w-5 rounded border-slate-700 bg-slate-950 text-brand-600 focus:ring-brand-500" />
    </label>
  );
}

function StatusBanner({ tone, message }: { tone: 'success' | 'warning' | 'error'; message: string }) {
  const classes = {
    success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
    warning: 'border-amber-500/30 bg-amber-500/10 text-amber-100',
    error: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
  }[tone];
  const Icon = tone === 'success' ? CheckCircle2 : tone === 'error' ? XCircle : AlertTriangle;
  return (
    <div className={`flex items-center gap-3 rounded-xl border p-3 text-sm ${classes}`}>
      <Icon className="h-5 w-5" />
      {message}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-slate-100">{value}</p>
    </div>
  );
}
