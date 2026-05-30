import { FormEvent, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileText, LineChart, Loader2, Play, Search, XCircle } from 'lucide-react';
import { lstmAPI } from '../api/lstm';
import { marketDataAPI } from '../api/marketData';
import { rlAPI } from '../api/rl';
import { simulationsAPI } from '../api/simulations';
import type { GeneratedCandleRow, LSTMGenerationResult, LSTMJob, LSTMTrainRequest, MarketDataResponse, OHLCVRow, RLTrainingJob, RLTrainingRequest, SimulationArtifact, SimulationRequest, SimulationRun } from '../types';

type SimulationForm = {
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  output_dir: string;
  generated_steps: number;
  sequence_length: number;
  lstm_epochs: number;
  lstm_batch_size: number;
  lstm_learning_rate: number;
  lstm_units_1: number;
  lstm_units_2: number;
  rl_algorithm: string;
  rl_total_timesteps: number;
  initial_balance: number;
  grid_levels: number;
  grid_step_pct: number;
  martingale_factor: number;
  random_seed: number | null;
  train_lstm: boolean;
  train_rl: boolean;
  save_charts: boolean;
};

const defaultForm: SimulationForm = {
  symbol: 'TSLA',
  timeframe: '1d',
  start_date: '',
  end_date: '',
  output_dir: 'simulation_output',
  generated_steps: 50,
  sequence_length: 5,
  lstm_epochs: 1,
  lstm_batch_size: 8,
  lstm_learning_rate: 0.001,
  lstm_units_1: 16,
  lstm_units_2: 16,
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
  const [rlJob, setRlJob] = useState<RLTrainingJob | null>(null);
  const [lstmJob, setLstmJob] = useState<LSTMJob | null>(null);
  const [lstmGeneration, setLstmGeneration] = useState<LSTMGenerationResult | null>(null);
  const [artifacts, setArtifacts] = useState<SimulationArtifact[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTrainingRl, setIsTrainingRl] = useState(false);
  const [isTrainingLstm, setIsTrainingLstm] = useState(false);
  const [isGeneratingLstm, setIsGeneratingLstm] = useState(false);
  const [isLoadingArtifacts, setIsLoadingArtifacts] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rlError, setRlError] = useState<string | null>(null);
  const [lstmError, setLstmError] = useState<string | null>(null);
  const [marketData, setMarketData] = useState<MarketDataResponse | null>(null);
  const [marketDataError, setMarketDataError] = useState<string | null>(null);
  const [isLoadingMarketData, setIsLoadingMarketData] = useState(false);

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

  const previewMarketData = async () => {
    setIsLoadingMarketData(true);
    setMarketDataError(null);
    try {
      const response = await marketDataAPI.getOHLCV({
        symbol: form.symbol,
        timeframe: form.timeframe as MarketDataResponse['timeframe'],
        start_date: form.start_date || null,
        end_date: form.end_date || null,
      });
      setMarketData(response.data);
    } catch (previewError) {
      console.error('Failed to preview market data:', previewError);
      setMarketData(null);
      setMarketDataError('Market data could not be loaded. Check the symbol, dates, timeframe, and provider settings.');
    } finally {
      setIsLoadingMarketData(false);
    }
  };

  const trainStandaloneLstm = async () => {
    if (!marketData || marketData.rows.length === 0) {
      setLstmError('Preview market data before training the standalone LSTM generator.');
      return;
    }

    setIsTrainingLstm(true);
    setLstmError(null);
    setLstmGeneration(null);

    const payload: LSTMTrainRequest = {
      rows: marketData.rows,
      features: ['Open', 'High', 'Low', 'Close', 'Volume'],
      sequence_length: form.sequence_length,
      lstm_units_1: form.lstm_units_1,
      lstm_units_2: form.lstm_units_2,
      learning_rate: form.lstm_learning_rate,
      epochs: form.lstm_epochs,
      batch_size: form.lstm_batch_size,
      validation_split: 0,
    };

    try {
      const response = await lstmAPI.train(payload);
      setLstmJob(response.data);
    } catch (trainingError) {
      console.error('Failed to train LSTM generator:', trainingError);
      setLstmError('Failed to train LSTM generator. Use at least sequence length + 2 preview rows and try smoke-test settings first.');
    } finally {
      setIsTrainingLstm(false);
    }
  };

  const generateStandaloneLstm = async () => {
    if (!lstmJob || lstmJob.status !== 'completed') {
      setLstmError('Train a completed LSTM job before generating synthetic candles.');
      return;
    }

    setIsGeneratingLstm(true);
    setLstmError(null);

    try {
      const response = await lstmAPI.generate({
        job_id: lstmJob.id,
        num_steps: form.generated_steps || 25,
      });
      setLstmGeneration(response.data);
    } catch (generationError) {
      console.error('Failed to generate LSTM candles:', generationError);
      setLstmError('Failed to generate synthetic candles from the selected LSTM job.');
    } finally {
      setIsGeneratingLstm(false);
    }
  };

  const refreshLstmJob = async () => {
    if (!lstmJob) {
      return;
    }
    try {
      const response = await lstmAPI.getJob(lstmJob.id);
      setLstmJob(response.data);
    } catch (refreshError) {
      console.error('Failed to refresh LSTM job:', refreshError);
      setLstmError('Failed to refresh LSTM training status.');
    }
  };

  const startRlTraining = async () => {
    setIsTrainingRl(true);
    setRlError(null);

    const payload: RLTrainingRequest = {
      algorithm: form.rl_algorithm as RLTrainingRequest['algorithm'],
      total_timesteps: form.rl_total_timesteps,
      hyperparameters: {},
      policy: 'MlpPolicy',
      model_name: `${form.symbol.toLowerCase()}_${form.rl_algorithm.toLowerCase()}_pivot`,
      save_model: true,
      seed: form.random_seed ?? null,
      environment: 'pivot-grid',
      symbol: form.symbol,
      timeframe: form.timeframe,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      output_dir: `${form.output_dir}/rl_training`,
      generated_steps: form.generated_steps || null,
      initial_balance: form.initial_balance,
      grid_levels: form.grid_levels,
      grid_step_pct: form.grid_step_pct,
      martingale_factor: form.martingale_factor,
    };

    try {
      const response = await rlAPI.train(payload);
      setRlJob(response.data);
    } catch (trainingError) {
      console.error('Failed to start RL training:', trainingError);
      setRlError('Failed to start RL training. Pivot-grid supports PPO, DQN, and A2C; SAC requires a continuous-action environment.');
    } finally {
      setIsTrainingRl(false);
    }
  };

  const refreshRlJob = async () => {
    if (!rlJob) {
      return;
    }
    try {
      const response = await rlAPI.getJob(rlJob.id);
      setRlJob(response.data);
    } catch (refreshError) {
      console.error('Failed to refresh RL training job:', refreshError);
      setRlError('Failed to refresh RL training status.');
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
            <NumberField label="LSTM sequence length" value={form.sequence_length} onChange={(value) => updateForm('sequence_length', value)} />
            <NumberField label="LSTM units layer 1" value={form.lstm_units_1} onChange={(value) => updateForm('lstm_units_1', value)} />
            <NumberField label="LSTM units layer 2" value={form.lstm_units_2} onChange={(value) => updateForm('lstm_units_2', value)} />
            <NumberField label="LSTM epochs" value={form.lstm_epochs} onChange={(value) => updateForm('lstm_epochs', value)} />
            <NumberField label="LSTM batch size" value={form.lstm_batch_size} onChange={(value) => updateForm('lstm_batch_size', value)} />
            <NumberField label="LSTM learning rate" step="0.0001" value={form.lstm_learning_rate} onChange={(value) => updateForm('lstm_learning_rate', value)} />
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

          <MarketDataPreview
            data={marketData}
            error={marketDataError}
            isLoading={isLoadingMarketData}
            onPreview={previewMarketData}
          />

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
          <LSTMGenerationPanel
            job={lstmJob}
            generation={lstmGeneration}
            error={lstmError}
            isTraining={isTrainingLstm}
            isGenerating={isGeneratingLstm}
            hasMarketData={Boolean(marketData?.rows.length)}
            onTrain={trainStandaloneLstm}
            onGenerate={generateStandaloneLstm}
            onRefresh={refreshLstmJob}
          />
          <RLTrainingPanel
            job={rlJob}
            error={rlError}
            isTraining={isTrainingRl}
            selectedAlgorithm={form.rl_algorithm}
            onStart={startRlTraining}
            onRefresh={refreshRlJob}
          />
          <ResultSummary simulation={simulation} onRefresh={refreshSimulation} />
          <ArtifactList artifacts={artifacts} isLoading={isLoadingArtifacts} />
        </aside>
      </section>
    </div>
  );
}


function LSTMGenerationPanel({
  job,
  generation,
  error,
  isTraining,
  isGenerating,
  hasMarketData,
  onTrain,
  onGenerate,
  onRefresh,
}: {
  job: LSTMJob | null;
  generation: LSTMGenerationResult | null;
  error: string | null;
  isTraining: boolean;
  isGenerating: boolean;
  hasMarketData: boolean;
  onTrain: () => void;
  onGenerate: () => void;
  onRefresh: () => void;
}) {
  const statusTone = job?.status === 'completed' ? 'success' : job?.status === 'failed' ? 'error' : 'warning';
  const canGenerate = job?.status === 'completed';

  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
      <div>
        <h3 className="text-xl font-semibold text-white">Synthetic data (LSTM)</h3>
        <p className="mt-1 text-sm text-slate-400">
          Train a standalone LSTM generator from the market-data preview, then generate synthetic OHLCV candles for simulations.
        </p>
      </div>

      {!hasMarketData && <StatusBanner tone="warning" message="Preview market data first so the LSTM trainer has source candles." />}
      {error && <StatusBanner tone="error" message={error} />}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={isTraining || !hasMarketData}
          onClick={onTrain}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isTraining ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {isTraining ? 'Training...' : 'Train LSTM'}
        </button>
        <button
          type="button"
          disabled={isGenerating || !canGenerate}
          onClick={onGenerate}
          className="inline-flex items-center gap-2 rounded-xl border border-brand-500/60 px-4 py-2 text-sm font-semibold text-brand-100 hover:bg-brand-500/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <LineChart className="h-4 w-4" />}
          {isGenerating ? 'Generating...' : 'Generate candles'}
        </button>
        {job && (
          <button type="button" onClick={onRefresh} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800">
            Refresh status
          </button>
        )}
      </div>

      {job ? (
        <div className="space-y-3">
          <StatusBanner tone={statusTone} message={`LSTM job status: ${job.status}`} />
          <p className="break-all text-xs text-slate-500">Job ID: {job.id}</p>
          {job.error && <StatusBanner tone="error" message={job.error} />}
          {job.result && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Metric label="Features" value={job.result.features.join(', ')} />
              <Metric label="Rows trained" value={job.result.row_count.toString()} />
              <Metric label="Sequence length" value={job.result.sequence_length.toString()} />
              <Metric label="Final loss" value={job.result.final_loss === null ? 'n/a' : formatNumber(job.result.final_loss, 6)} />
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-400">No standalone LSTM job has been started from this page.</p>
      )}

      {generation && (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Metric label="Generated rows" value={generation.row_count.toString()} />
            <Metric label="Generated features" value={generation.features.join(', ')} />
          </div>
          <GeneratedCandleChart rows={generation.rows} />
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="min-w-full divide-y divide-slate-800 text-sm">
              <thead className="bg-slate-900/80 text-left text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-3 py-2">Step</th>
                  <th className="px-3 py-2">Open</th>
                  <th className="px-3 py-2">High</th>
                  <th className="px-3 py-2">Low</th>
                  <th className="px-3 py-2">Close</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-200">
                {generation.rows.slice(0, 6).map((row) => (
                  <tr key={row.step}>
                    <td className="px-3 py-2 text-slate-400">{row.step}</td>
                    <td className="px-3 py-2">{formatOptionalNumber(row.open)}</td>
                    <td className="px-3 py-2">{formatOptionalNumber(row.high)}</td>
                    <td className="px-3 py-2">{formatOptionalNumber(row.low)}</td>
                    <td className="px-3 py-2 font-medium text-white">{formatOptionalNumber(row.close)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function RLTrainingPanel({
  job,
  error,
  isTraining,
  selectedAlgorithm,
  onStart,
  onRefresh,
}: {
  job: RLTrainingJob | null;
  error: string | null;
  isTraining: boolean;
  selectedAlgorithm: string;
  onStart: () => void;
  onRefresh: () => void;
}) {
  const statusTone = job?.status === 'completed' ? 'success' : job?.status === 'failed' ? 'error' : 'warning';
  const isUnsupportedPivotAlgorithm = selectedAlgorithm === 'SAC';

  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
      <div>
        <h3 className="text-xl font-semibold text-white">RL training</h3>
        <p className="mt-1 text-sm text-slate-400">
          Train a standalone pivot-grid policy from the current simulation data and environment settings.
        </p>
      </div>

      {isUnsupportedPivotAlgorithm && (
        <StatusBanner tone="warning" message="SAC is listed for future continuous environments; pivot-grid training currently supports PPO, DQN, and A2C." />
      )}
      {error && <StatusBanner tone="error" message={error} />}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={isTraining || isUnsupportedPivotAlgorithm}
          onClick={onStart}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isTraining ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {isTraining ? 'Training...' : 'Train RL model'}
        </button>
        {job && (
          <button type="button" onClick={onRefresh} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800">
            Refresh status
          </button>
        )}
      </div>

      {job ? (
        <div className="space-y-3">
          <StatusBanner tone={statusTone} message={`RL job status: ${job.status}`} />
          <p className="break-all text-xs text-slate-500">Job ID: {job.id}</p>
          {job.error && <StatusBanner tone="error" message={job.error} />}
          {job.result && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Metric label="Algorithm" value={job.result.algorithm} />
              <Metric label="Timesteps" value={job.result.total_timesteps.toString()} />
              <Metric label="Environment" value={job.result.environment} />
              <Metric label="Artifact ID" value={job.result.artifact_id ?? 'Not saved'} />
              {job.result.model_path && <Metric label="Model path" value={job.result.model_path} />}
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-400">No standalone RL training job has been started from this page.</p>
      )}
    </div>
  );
}

function MarketDataPreview({
  data,
  error,
  isLoading,
  onPreview,
}: {
  data: MarketDataResponse | null;
  error: string | null;
  isLoading: boolean;
  onPreview: () => void;
}) {
  const previewRows = data?.rows.slice(0, 6) ?? [];
  const chartRows = data?.rows.slice(-24) ?? [];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-lg font-semibold text-white">
            <LineChart className="h-5 w-5 text-brand-300" />
            Market data preview
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Load backend-fetched OHLCV rows before running a simulation with the same symbol, timeframe, and date range.
          </p>
        </div>
        <button
          type="button"
          onClick={onPreview}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-brand-500/60 px-4 py-2 text-sm font-semibold text-brand-100 hover:bg-brand-500/10 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          {isLoading ? 'Loading...' : 'Preview data'}
        </button>
      </div>

      {error && <div className="mt-4"><StatusBanner tone="error" message={error} /></div>}

      {data && (
        <div className="mt-5 space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Rows" value={data.row_count.toString()} />
            <Metric label="Symbol" value={data.symbol} />
            <Metric label="Timeframe" value={data.timeframe} />
          </div>

          <ClosePreviewChart rows={chartRows} />

          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="min-w-full divide-y divide-slate-800 text-sm">
              <thead className="bg-slate-900/80 text-left text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Open</th>
                  <th className="px-3 py-2">High</th>
                  <th className="px-3 py-2">Low</th>
                  <th className="px-3 py-2">Close</th>
                  <th className="px-3 py-2">Volume</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-200">
                {previewRows.map((row) => (
                  <tr key={row.timestamp}>
                    <td className="whitespace-nowrap px-3 py-2 text-slate-400">{formatTimestamp(row.timestamp)}</td>
                    <td className="px-3 py-2">{formatNumber(row.open)}</td>
                    <td className="px-3 py-2">{formatNumber(row.high)}</td>
                    <td className="px-3 py-2">{formatNumber(row.low)}</td>
                    <td className="px-3 py-2 font-medium text-white">{formatNumber(row.close)}</td>
                    <td className="px-3 py-2">{formatNumber(row.volume, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}


function GeneratedCandleChart({ rows }: { rows: GeneratedCandleRow[] }) {
  const chartRows = rows.filter((row) => row.close !== null).slice(-24);
  if (chartRows.length < 2) {
    return <p className="text-sm text-slate-500">Generate at least two synthetic rows to draw a close-price sparkline.</p>;
  }

  const closes = chartRows.map((row) => row.close ?? 0);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const points = chartRows
    .map((row, index) => {
      const x = (index / (chartRows.length - 1)) * 100;
      const y = 100 - (((row.close ?? min) - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
      <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
        <span>Synthetic close preview</span>
        <span>{formatNumber(min)} – {formatNumber(max)}</span>
      </div>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-24 w-full overflow-visible">
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-300" vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  );
}

function ClosePreviewChart({ rows }: { rows: OHLCVRow[] }) {
  if (rows.length < 2) {
    return <p className="text-sm text-slate-500">Load at least two rows to draw a close-price sparkline.</p>;
  }

  const closes = rows.map((row) => row.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const points = rows
    .map((row, index) => {
      const x = (index / (rows.length - 1)) * 100;
      const y = 100 - ((row.close - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
      <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
        <span>Close preview</span>
        <span>{formatNumber(min)} – {formatNumber(max)}</span>
      </div>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-24 w-full overflow-visible">
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" className="text-brand-300" vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  );
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatNumber(value: number, maximumFractionDigits = 4) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits }).format(value);
}

function formatOptionalNumber(value: number | null, maximumFractionDigits = 4) {
  return value === null ? 'n/a' : formatNumber(value, maximumFractionDigits);
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
