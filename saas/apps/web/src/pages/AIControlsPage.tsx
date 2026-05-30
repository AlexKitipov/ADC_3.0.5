import { FormEvent, useState } from 'react';
import { lstmAPI } from '../api/lstm';
import { marketDataAPI } from '../api/marketData';
import { rlAPI } from '../api/rl';
import { EmptyState, ErrorState, StatusBanner } from '../components/PageState';
import type { LSTMGenerationResult, LSTMJob, OHLCVRow, RLAlgorithm, RLTrainingJob } from '../types';

export async function startLstmTraining(rows: OHLCVRow[]) {
  if (rows.length < 3) {
    throw new Error('LSTM training requires at least three OHLCV rows.');
  }
  const response = await lstmAPI.train({ rows, sequence_length: 2, epochs: 1, batch_size: 2 });
  return response.data;
}

export async function startRlTraining(symbol: string, algorithm: RLAlgorithm, totalTimesteps: number) {
  if (!symbol.trim()) {
    throw new Error('Symbol is required.');
  }
  if (!Number.isFinite(totalTimesteps) || totalTimesteps <= 0) {
    throw new Error('RL timesteps must be greater than zero.');
  }
  const response = await rlAPI.train({ symbol: symbol.trim().toUpperCase(), algorithm, total_timesteps: totalTimesteps, environment: 'pivot-grid' });
  return response.data;
}

export function AIControlsPage() {
  const [symbol, setSymbol] = useState('EURUSD');
  const [algorithm, setAlgorithm] = useState<RLAlgorithm>('PPO');
  const [timesteps, setTimesteps] = useState('1000');
  const [rows, setRows] = useState<OHLCVRow[]>([]);
  const [lstmJob, setLstmJob] = useState<LSTMJob | null>(null);
  const [generation, setGeneration] = useState<LSTMGenerationResult | null>(null);
  const [rlJob, setRlJob] = useState<RLTrainingJob | null>(null);
  const [isLoadingRows, setIsLoadingRows] = useState(false);
  const [isTrainingLstm, setIsTrainingLstm] = useState(false);
  const [isTrainingRl, setIsTrainingRl] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRows = async () => {
    setIsLoadingRows(true);
    setError(null);
    try {
      const response = await marketDataAPI.getOHLCV({ symbol: symbol.trim().toUpperCase(), timeframe: '1d' });
      setRows(response.data.rows);
    } catch (loadError) {
      console.error('Failed to load LSTM seed rows:', loadError);
      setRows([]);
      setError('Market data rows could not be loaded for AI training.');
    } finally {
      setIsLoadingRows(false);
    }
  };

  const trainLstm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsTrainingLstm(true);
    setError(null);
    setGeneration(null);
    try {
      const job = await startLstmTraining(rows);
      setLstmJob(job);
    } catch (trainingError) {
      console.error('Failed to start LSTM training:', trainingError);
      setError(trainingError instanceof Error ? trainingError.message : 'LSTM training could not be started.');
    } finally {
      setIsTrainingLstm(false);
    }
  };

  const generateCandles = async () => {
    if (!lstmJob) {
      return;
    }
    setError(null);
    try {
      const response = await lstmAPI.generate({ job_id: lstmJob.id, num_steps: 5, seed_rows: rows.slice(-5) });
      setGeneration(response.data);
    } catch (generateError) {
      console.error('Failed to generate LSTM candles:', generateError);
      setError('LSTM generation could not be completed yet. Refresh the job after it finishes.');
    }
  };

  const trainRl = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsTrainingRl(true);
    setError(null);
    try {
      setRlJob(await startRlTraining(symbol, algorithm, Number(timesteps)));
    } catch (trainingError) {
      console.error('Failed to start RL training:', trainingError);
      setError(trainingError instanceof Error ? trainingError.message : 'RL training could not be started.');
    } finally {
      setIsTrainingRl(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-white">RL / LSTM Controls</h2>
        <p className="mt-2 text-slate-400">Standalone training controls for the backend LSTM generator and pivot-grid reinforcement-learning jobs.</p>
      </div>

      {error && <ErrorState message={error} />}

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <label className="w-full text-sm font-medium text-slate-300 md:max-w-xs">
            Training symbol
            <input value={symbol} onChange={(event) => setSymbol(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-brand-500" />
          </label>
          <button type="button" onClick={loadRows} disabled={isLoadingRows} className="rounded-lg border border-brand-500/40 px-4 py-2 text-sm font-semibold text-brand-200 hover:bg-brand-500/10 disabled:opacity-60">
            {isLoadingRows ? 'Loading rows...' : 'Load OHLCV seed rows'}
          </button>
        </div>
        <p className="mt-3 text-sm text-slate-400">{rows.length} OHLCV rows are ready for model training.</p>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <form onSubmit={trainLstm} className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-5">
          <h3 className="text-lg font-semibold text-cyan-100">LSTM generator</h3>
          <p className="mt-1 text-sm text-cyan-100/80">Train from loaded OHLCV rows, then request generated candle steps from /lstm/generate.</p>
          <button type="submit" disabled={isTrainingLstm || rows.length < 3} className="mt-4 rounded-lg bg-cyan-300 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-200 disabled:opacity-60">
            {isTrainingLstm ? 'Starting training...' : 'Train LSTM'}
          </button>
          {lstmJob ? <JobCard title="LSTM job" id={lstmJob.id} status={lstmJob.status} error={lstmJob.error} /> : <EmptyState title="No LSTM job" message="Load OHLCV rows and start a job to see model status here." />}
          {lstmJob && <button type="button" onClick={generateCandles} className="mt-4 rounded-lg border border-cyan-300/50 px-4 py-2 text-sm font-semibold text-cyan-100 hover:bg-cyan-300/10">Generate candles</button>}
          {generation && <StatusBanner tone="success" message={`Generated ${generation.row_count} candle rows from job ${generation.job_id}.`} />}
        </form>

        <form onSubmit={trainRl} className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5">
          <h3 className="text-lg font-semibold text-emerald-100">RL pivot-grid trainer</h3>
          <p className="mt-1 text-sm text-emerald-100/80">Start backend RL training with explicit algorithm and timestep parameters.</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-300">Algorithm<select value={algorithm} onChange={(event) => setAlgorithm(event.target.value as RLAlgorithm)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white"><option>PPO</option><option>DQN</option><option>A2C</option><option>SAC</option></select></label>
            <label className="text-sm font-medium text-slate-300">Timesteps<input type="number" min="1" value={timesteps} onChange={(event) => setTimesteps(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" /></label>
          </div>
          <button type="submit" disabled={isTrainingRl} className="mt-4 rounded-lg bg-emerald-300 px-4 py-2 font-semibold text-slate-950 hover:bg-emerald-200 disabled:opacity-60">
            {isTrainingRl ? 'Starting training...' : 'Train RL model'}
          </button>
          {rlJob ? <JobCard title="RL job" id={rlJob.id} status={rlJob.status} error={rlJob.error} /> : <EmptyState title="No RL job" message="Submit RL parameters to start a pivot-grid training job." />}
        </form>
      </section>
    </div>
  );
}

function JobCard({ title, id, status, error }: { title: string; id: string; status: string; error: string | null }) {
  return <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/50 p-4"><p className="text-xs uppercase tracking-wider text-slate-500">{title}</p><p className="mt-2 font-mono text-sm text-white">{id}</p><p className="mt-2 text-sm text-slate-300">Status: <span className="font-semibold text-white">{status}</span></p>{error && <p className="mt-2 text-sm text-rose-300">{error}</p>}</div>;
}
