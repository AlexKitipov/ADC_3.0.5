export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export type KnownSignalAction = 'BUY' | 'SELL' | 'HOLD';
export type SignalAction = KnownSignalAction | (string & Record<never, never>);

export interface Signal {
  id: number;
  symbol: string;
  action: SignalAction;
  price: number;
  rsi: number;
  macd: number;
  timestamp: string;
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
  status: 'open' | 'closed';
}

export interface DashboardStats {
  total_balance: number;
  current_equity: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  monthly_pnl: number;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  balance: number;
}

export interface DrawdownPoint {
  timestamp: string;
  drawdown: number;
}

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
