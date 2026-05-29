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

// Backward-compatible aliases retained for existing frontend modules.
export type TradeOpenRequest = TradeCreate;
export type TradeCloseRequest = TradeClose;
export type EquityPoint = EquityCurvePoint;
export type DrawdownPoint = DrawdownCurvePoint;
