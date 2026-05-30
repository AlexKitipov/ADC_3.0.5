/**
 * Frontend view of the backend API schemas.
 *
 * Source of truth: Pydantic models under `apps/api/app/schemas`. Keep exported
 * names aligned with backend schema names where practical until this package is
 * generated from OpenAPI or imported from `packages/contracts`.
 */

// Auth schemas: apps/api/app/schemas/auth.py
export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface UserCreate {
  email: string;
  username: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// Signal schemas: apps/api/app/schemas/signals.py
export type KnownSignalAction = 'BUY' | 'SELL' | 'HOLD';
export type SignalAction = KnownSignalAction | (string & Record<never, never>);

export interface SignalCreate {
  symbol: string;
  action: SignalAction;
  price: number;
  rsi: number;
  macd: number;
}

export interface Signal {
  id: number;
  symbol: string;
  action: SignalAction;
  price: number;
  rsi: number;
  macd: number;
  timestamp: string;
}

// Trade schemas: apps/api/app/schemas/trades.py
export interface TradeCreate {
  symbol: string;
  entry_price: number;
}

export interface TradeClose {
  exit_price: number;
}

export interface Trade {
  id: number;
  symbol: string;
  entry_price: number;
  exit_price: number | null;
  entry_time: string;
  exit_time: string | null;
  pnl: number | null;
  pnl_percent: number | null;
  status: 'open' | 'closed' | (string & Record<never, never>);
}


// Order schemas: apps/api/app/schemas/orders.py
export type OrderType = 'BUY' | 'SELL' | 'BUYSTOP' | 'SELLSTOP' | 'BUYLIMIT' | 'SELLLIMIT';

export interface OrderCreate {
  symbol: string;
  order_type: OrderType;
  volume: number;
  price: number;
  stop_loss?: number;
  take_profit?: number;
  slippage?: number;
  comment?: string;
  magic?: number;
}

export interface OrderClose {
  volume?: number | null;
  price: number;
  slippage?: number;
  exit_reason?: string;
}

export interface BrokerResult {
  status: string;
  error_code: number;
  message: string;
}

export interface Order {
  ticket: number;
  symbol: string;
  order_type: OrderType;
  volume: number;
  price: number;
  stop_loss: number;
  take_profit: number;
  slippage: number | null;
  status: string;
  broker_result: BrokerResult;
  open_time: string;
  close_price: number | null;
  close_time: string | null;
}


// Trading-session schemas: apps/api/app/schemas/sessions.py
export interface TradingSessionConfig {
  symbol?: string;
  initial_price?: number;
  price_volatility?: number;
  stream_interval?: number;
  order_volume?: number;
  slippage?: number;
  magic?: number;
  broker_error_rate?: number;
  broker_trade_allowed?: boolean;
  retry_attempts?: number;
  sleep_time?: number;
  sleep_maximum?: number;
  max_close_duration?: number;
  random_seed?: number | null;
}

export interface TradingSessionCreate {
  config?: TradingSessionConfig;
  auto_start?: boolean;
}

export interface SessionEvent {
  type: string;
  message: string;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface TradingSessionState {
  id: string;
  status: 'created' | 'running' | 'stopped';
  is_trading_active: boolean;
  broker_trade_allowed: boolean;
  symbol: string;
  config: Required<Omit<TradingSessionConfig, 'random_seed'>> & { random_seed: number | null };
  last_tick: Record<string, unknown> | null;
  last_action: unknown;
  open_positions: number;
  event_count: number;
  created_at: string;
  updated_at: string;
}

// Dashboard schemas: apps/api/app/schemas/dashboard.py
export interface DashboardStats {
  total_balance: number;
  current_equity: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  monthly_pnl: number;
}

export interface EquityCurvePoint {
  timestamp: string;
  equity: number;
  balance: number;
}

export interface DrawdownCurvePoint {
  timestamp: string;
  drawdown: number;
}

// Settings schemas: apps/api/app/schemas/settings.py
export interface UserSettingsUpdate {
  symbols: string[];
  timeframe: string;
  balance: number;
  /** Decimal fraction risk per trade; 0.02 means 2%. */
  risk_per_trade: number;
  grid_levels: number;
  /** Decimal fraction grid step; 0.005 means 0.5%. */
  grid_step_pct: number;
  martingale_factor: number;
  enable_trading: boolean;
  email_notifications: boolean;
}

export interface UserSettings extends UserSettingsUpdate {
  id: number;
}

// Strategy metadata schemas: apps/api/app/schemas/strategy.py
export type StrategyParameterValue = string | number | boolean | null;

export interface StrategyParameterSpec {
  name: string;
  group: string;
  label: string;
  default: StrategyParameterValue;
  min_value: number | null;
  max_value: number | null;
  step: number | null;
  options: StrategyParameterValue[];
  description: string;
}

// Backward-compatible aliases retained for existing frontend modules.
export type TradeOpenRequest = TradeCreate;
export type TradeCloseRequest = TradeClose;
export type EquityPoint = EquityCurvePoint;
export type DrawdownPoint = DrawdownCurvePoint;


// Market data schemas: apps/api/app/schemas/market_data.py
export interface MarketTick {
  symbol: string;
  price: number;
  bid: number;
  ask: number;
  timestamp: string;
}

export type MarketDataTimeframe = '1d' | '1min' | '5min' | '15min' | '30min' | '60min';

export interface MarketDataRequest {
  symbol: string;
  timeframe: MarketDataTimeframe;
  start_date?: string | null;
  end_date?: string | null;
}

export interface OHLCVRow {
  timestamp: string;
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketDataResponse extends MarketDataRequest {
  rows: OHLCVRow[];
  row_count: number;
}

// Indicator schemas: apps/api/app/schemas/indicators.py
export type IndicatorCalculationMode = 'stateless';

export interface IndicatorParameters {
  rsi_period: number;
  macd_fast: number;
  macd_slow: number;
  macd_signal: number;
  bollinger_period: number;
  bollinger_std: number;
  atr_period: number;
}

export interface IndicatorCalculationRequest {
  rows: OHLCVRow[];
  parameters?: IndicatorParameters;
}

export interface IndicatorValues {
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  bollinger_upper: number | null;
  bollinger_middle: number | null;
  bollinger_lower: number | null;
  atr: number | null;
  pivot: number | null;
  r1: number | null;
  s1: number | null;
  r2: number | null;
  s2: number | null;
  rsi_crosses: number;
}

export interface IndicatorRow {
  timestamp: string;
  symbol: string;
  close: number;
  indicators: IndicatorValues;
}

export interface IndicatorCalculationResponse {
  calculation_mode: IndicatorCalculationMode;
  row_count: number;
  parameters: IndicatorParameters;
  rows: IndicatorRow[];
}


// LSTM generation schemas: apps/api/app/schemas/lstm.py
export interface LSTMTrainRequest {
  rows: OHLCVRow[];
  features?: string[];
  sequence_length?: number;
  lstm_units_1?: number;
  lstm_units_2?: number;
  learning_rate?: number;
  epochs?: number;
  batch_size?: number;
  validation_split?: number;
}

export interface LSTMTrainingResult {
  features: string[];
  sequence_length: number;
  lstm_units_1: number;
  lstm_units_2: number;
  learning_rate: number;
  epochs: number;
  batch_size: number;
  row_count: number;
  final_loss: number | null;
  final_val_loss: number | null;
  message: string;
}

export interface LSTMJob {
  id: string;
  status: 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at: string | null;
  request: Record<string, unknown>;
  result: LSTMTrainingResult | null;
  error: string | null;
}

export interface LSTMGenerateRequest {
  job_id: string;
  num_steps?: number;
  seed_rows?: OHLCVRow[] | null;
}

export interface GeneratedCandleRow {
  step: number;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  features: Record<string, number>;
}

export interface LSTMGenerationResult {
  job_id: string;
  features: string[];
  rows: GeneratedCandleRow[];
  row_count: number;
}

// RL training schemas: apps/api/app/schemas/rl.py
export type RLAlgorithm = 'PPO' | 'DQN' | 'A2C' | 'SAC';
export type RLEnvironment = 'pivot-grid';
export type RLTrainingStatus = 'running' | 'completed' | 'failed';

export interface RLTrainingRequest {
  algorithm: RLAlgorithm;
  total_timesteps: number;
  hyperparameters?: Record<string, unknown>;
  policy?: string;
  model_name?: string | null;
  save_model?: boolean;
  seed?: number | null;
  verbose?: number;
  device?: string;
  environment?: RLEnvironment;
  symbol?: string;
  timeframe?: string;
  start_date?: string | null;
  end_date?: string | null;
  alpha_vantage_api_key?: string | null;
  output_dir?: string;
  generated_steps?: number | null;
  initial_balance?: number;
  grid_levels?: number;
  grid_step_pct?: number;
  martingale_factor?: number;
}

export interface RLTrainingResult {
  algorithm: string;
  total_timesteps: number;
  hyperparameters: Record<string, unknown>;
  environment: string;
  model_path: string | null;
  artifact_id: string | null;
}

export interface RLTrainingJob {
  id: string;
  status: RLTrainingStatus;
  created_at: string;
  completed_at: string | null;
  request: Record<string, unknown>;
  result: RLTrainingResult | null;
  error: string | null;
}

export interface RLModelArtifact {
  id: string;
  job_id: string;
  algorithm: string;
  path: string;
  exists: boolean;
  size_bytes: number | null;
  created_at: string;
}

// Simulation schemas: apps/api/app/schemas/simulations.py
export interface SimulationRequest {
  symbol?: string;
  timeframe?: string;
  start_date?: string | null;
  end_date?: string | null;
  output_dir?: string;
  generated_steps?: number | null;
  sequence_length?: number | null;
  lstm_epochs?: number | null;
  lstm_batch_size?: number | null;
  lstm_learning_rate?: number | null;
  lstm_units_1?: number | null;
  lstm_units_2?: number | null;
  train_lstm?: boolean;
  train_rl?: boolean;
  save_charts?: boolean;
  rl_algorithm?: string;
  rl_total_timesteps?: number;
  initial_balance?: number;
  grid_levels?: number;
  grid_step_pct?: number;
  martingale_factor?: number;
  random_seed?: number | null;
}

export interface SimulationResult {
  output_dir: string;
  historical_data_path: string;
  generated_data_path: string;
  orders_path: string;
  trades_path: string;
  performance_path: string;
  rewards_path: string;
  equity_curve_path: string;
  drawdown_path: string;
  model_path: string | null;
  equity_chart_path: string | null;
  drawdown_chart_path: string | null;
  performance: Record<string, string | number | boolean | null>;
  total_steps: number;
  trained_lstm: boolean;
  trained_rl: boolean;
}

export interface SimulationRun {
  id: string;
  status: 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at: string | null;
  parameters: Record<string, string | number | boolean | null | object>;
  result: SimulationResult | null;
  error: string | null;
}

export interface SimulationArtifact {
  name: string;
  path: string;
  exists: boolean;
  size_bytes: number | null;
}
