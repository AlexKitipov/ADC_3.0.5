import { FormEvent, useEffect, useState } from "react";
import { settingsAPI } from "../api/settings";
import { LoadingState } from "../components/LoadingState";
import { UserSettings } from "../types";

const defaultSettings: UserSettings = {
  symbols: ["BTCUSDT", "ETHUSDT"],
  timeframe: "1h",
  balance: 10000,
  risk_per_trade: 0.02,
  grid_levels: 5,
  grid_step_pct: 1,
  martingale_factor: 1.5,
  enable_trading: false,
  email_notifications: true,
};

export function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [symbols, setSymbols] = useState(defaultSettings.symbols.join(", "));
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    settingsAPI
      .getUserSettings()
      .then((response) => {
        const userSettings = response.data ?? defaultSettings;
        setSettings(userSettings);
        setSymbols(userSettings.symbols.join(", "));
      })
      .catch((fetchError) => {
        console.error("Failed to fetch settings:", fetchError);
        setError("Failed to load settings. Please refresh and try again.");
      })
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    if (!saved) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setSaved(false), 3000);
    return () => window.clearTimeout(timeoutId);
  }, [saved]);

  const updateSettings = (nextSettings: Partial<UserSettings>) => {
    setSettings((currentSettings) =>
      currentSettings
        ? { ...currentSettings, ...nextSettings }
        : currentSettings,
    );
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();

    if (!settings) {
      return;
    }

    const nextSettings = {
      ...settings,
      symbols: symbols
        .split(",")
        .map((symbol) => symbol.trim())
        .filter(Boolean),
    };

    try {
      await settingsAPI.updateUserSettings(nextSettings);
      setSettings(nextSettings);
      setError(null);
      setSaved(true);
    } catch (saveError) {
      console.error("Failed to save settings:", saveError);
      setSaved(false);
      setError(
        "Failed to save settings. Please check your values and try again.",
      );
    }
  };

  if (isLoading) {
    return <LoadingState label="Loading settings..." />;
  }

  if (!settings) {
    return (
      <p className="rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
        {error ?? "Failed to load settings."}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Settings</h2>
        <p className="mt-2 text-slate-400">
          Configure trading preferences and notifications.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="max-w-3xl space-y-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6"
      >
        <label className="block">
          <span className="text-sm text-slate-300">Trading Symbols</span>
          <input
            value={symbols}
            onChange={(event) => setSymbols(event.target.value)}
            placeholder="BTCUSDT, ETHUSDT"
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
          />
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <NumberField
            label="Account Balance"
            value={settings.balance}
            onChange={(value) => updateSettings({ balance: value })}
          />
          <NumberField
            label="Risk Per Trade (%)"
            value={settings.risk_per_trade * 100}
            step="0.1"
            onChange={(value) =>
              updateSettings({ risk_per_trade: value / 100 })
            }
          />
          <NumberField
            label="Grid Levels"
            value={settings.grid_levels}
            onChange={(value) => updateSettings({ grid_levels: value })}
          />
          <NumberField
            label="Grid Step %"
            value={settings.grid_step_pct}
            step="0.1"
            onChange={(value) => updateSettings({ grid_step_pct: value })}
          />
          <NumberField
            label="Martingale Factor"
            value={settings.martingale_factor}
            step="0.1"
            onChange={(value) => updateSettings({ martingale_factor: value })}
          />
          <label className="block">
            <span className="text-sm text-slate-300">Timeframe</span>
            <select
              value={settings.timeframe}
              onChange={(event) =>
                updateSettings({ timeframe: event.target.value })
              }
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
            >
              <option value="5m">5 Minutes</option>
              <option value="15m">15 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="4h">4 Hours</option>
              <option value="1d">Daily</option>
            </select>
          </label>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <Toggle
            label="Enable Trading"
            checked={settings.enable_trading}
            onChange={(value) => updateSettings({ enable_trading: value })}
          />
          <Toggle
            label="Email Notifications"
            checked={settings.email_notifications}
            onChange={(value) => updateSettings({ email_notifications: value })}
          />
        </div>

        {saved && (
          <p className="rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
            Settings saved successfully!
          </p>
        )}
        {error && (
          <p className="rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="w-full rounded-xl bg-brand-600 px-5 py-3 font-semibold text-white hover:bg-brand-700 md:w-auto"
        >
          Save Settings
        </button>
      </form>
    </div>
  );
}

function NumberField({
  label,
  value,
  step = "1",
  onChange,
}: {
  label: string;
  value: number;
  step?: string;
  onChange: (value: number) => void;
}) {
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

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 px-4 py-3">
      <span className="text-sm text-slate-300">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-5 w-5 accent-brand-600"
      />
    </label>
  );
}
