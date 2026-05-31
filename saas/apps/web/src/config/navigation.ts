import {
  Activity,
  BarChart3,
  Beaker,
  Bell,
  BookOpen,
  BrainCircuit,
  Database,
  Radio,
  Settings,
  Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  description: string;
};

export const mvpNavItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3, description: 'Equity, drawdown, live status' },
  { to: '/settings', label: 'Settings', icon: Settings, description: 'Risk and preferences' },
  { to: '/signals', label: 'Signals', icon: Zap, description: 'Indicator-driven ideas' },
  { to: '/trades', label: 'Trades / History', icon: Activity, description: 'Orders and trade records' },
];

export const labNavItems: NavItem[] = [
  { to: '/market-data', label: 'Market Data', icon: Database, description: 'OHLCV and indicators' },
  { to: '/sessions', label: 'Sessions', icon: Radio, description: 'Runtime controls and events' },
  { to: '/trade-journal', label: 'Trade Journal', icon: BookOpen, description: 'Artifacts and exports' },
  { to: '/simulations', label: 'Simulations', icon: Beaker, description: 'Strategy experiments' },
  { to: '/ai-controls', label: 'RL / LSTM', icon: BrainCircuit, description: 'Standalone model jobs' },
  { to: '/notifications', label: 'Notifications', icon: Bell, description: 'Delivery tests' },
];
