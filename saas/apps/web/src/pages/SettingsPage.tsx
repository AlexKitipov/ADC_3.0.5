import { FormEvent, useEffect, useState } from 'react';
import { settingsAPI } from '../api/settings';
import { LoadingState } from '../components/LoadingState';
import { UserSettings } from '../types';

const defaultSettings: UserSettings = {
  symbols: ['BTCUSDT', 'ETHUSDT'],
  timeframe: '1h',
  balance: 10000,
  risk_per_trade: 0.02,
  grid_levels: 5,
  grid_step_pct: 1,
  martingale_factor: 1.5,
  enable_trading: false,
  email_notifications: true,
};

export function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>(defaultSettings);
  const [symbols, setSymbols] = useState(defaultSettings.symbols.join(', '));
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    settingsAPI
      .getUserSettings()
      .then((response) => {
        if (response.data) {
          setSettings(response.data);
          setSymbols(response.data.symbols.join(', '));
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const nextSettings = {
      ...settings,
      symbols: symbols.split(',').map((symbol) => symbol.trim()).filter(Boolean),
    };
    await settingsAPI.updateUserSettings(nextSettings);
    setSettings(nextSettings);
    setMessage('Settings saved successfully.');
  };

  if (isLoading) {
    return <LoadingState label="Loading settings..." />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Settings</h2>
        <p className="mt-2 text-slate-400">Configure trading preferences and notifications.</p>
      </div>

      <form onSubmit={handleSubmit} className="max-w-3xl space-y-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <label className="block">
          <span className="text-sm text-slate-300">Symbols</span>
          <input
            value={symbols}
            onChange={(event) => setSymbols(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
          />
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <NumberField label="Balance" value={settings.balance} onChange={(value) => setSettings({ ...settings, balance: value })} />
          <NumberField label="Risk Per Trade" value={settings.risk_per_trade} step="0.01" onChange={(value) => setSettings({ ...settings, risk_per_trade: value })} />
          <NumberField label="Grid Levels" value={settings.grid_levels} onChange={(value) => setSettings({ ...settings, grid_levels: value })} />
          <NumberField label="Grid Step %" value={settings.grid_step_pct} step="0.1" onChange={(value) => setSettings({ ...settings, grid_step_pct: value })} />
          <NumberField label="Martingale Factor" value={settings.martingale_factor} step="0.1" onChange={(value) => setSettings({ ...settings, martingale_factor: value })} />
          <label className="block">
            <span className="text-sm text-slate-300">Timeframe</span>
            <select
              value={settings.timeframe}
              onChange={(event) => setSettings({ ...settings, timeframe: event.target.value })}
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
            >
              {['5m', '15m', '1h', '4h', '1d'].map((timeframe) => (
                <option key={timeframe} value={timeframe}>{timeframe}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <Toggle label="Enable Trading" checked={settings.enable_trading} onChange={(value) => setSettings({ ...settings, enable_trading: value })} />
          <Toggle label="Email Notifications" checked={settings.email_notifications} onChange={(value) => setSettings({ ...settings, email_notifications: value })} />
        </div>

        {message && <p className="rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">{message}</p>}

        <button type="submit" className="rounded-xl bg-brand-600 px-5 py-3 font-semibold text-white hover:bg-brand-700">
          Save settings
        </button>
      </form>
    </div>
  );
}

function NumberField({ label, value, step = '1', onChange }: { label: string; value: number; step?: string; onChange: (value: number) => void }) {
  return (
    <label className="block">
      <span className="text-sm text-slate-300">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
      />
    </label>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 px-4 py-3">
      <span className="text-sm text-slate-300">{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-5 w-5 accent-brand-600" />
    </label>
  );
}
