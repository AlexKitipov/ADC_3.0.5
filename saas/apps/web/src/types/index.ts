export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface Signal {
  id: number;
  symbol: string;
  action: 'BUY' | 'SELL' | 'HOLD';
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

export interface UserSettings {
  symbols: string[];
  timeframe: string;
  balance: number;
  risk_per_trade: number;
  grid_levels: number;
  grid_step_pct: number;
  martingale_factor: number;
  enable_trading: boolean;
  email_notifications: boolean;
}
