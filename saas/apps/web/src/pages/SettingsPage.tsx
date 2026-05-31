import { FormEvent, useEffect, useState } from "react";
import { notificationsAPI } from "../api/notifications";
import { settingsAPI } from "../api/settings";
import { LoadingState } from "../components/LoadingState";
import { SettingsTimeframe, UserSettings, UserSettingsUpdate } from "../types";

function parseSymbols(symbols: string) {
  return Array.from(
    new Set(
      symbols
        .split(",")
        .map((symbol) => symbol.trim().toUpperCase())
        .filter(Boolean),
    ),
  );
}

export function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [symbols, setSymbols] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [isTestingNotification, setIsTestingNotification] = useState(false);
  const [notificationStatus, setNotificationStatus] = useState<string | null>(
    null,
  );

  useEffect(() => {
    settingsAPI
      .getUserSettings()
      .then((response) => {
        setSettings(response.data);
        setSymbols(response.data.symbols.join(", "));
        setError(null);
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

  const clearValidationState = () => {
    setError(null);
    setSaved(false);
  };

  const updateSettings = (nextSettings: Partial<UserSettingsUpdate>) => {
    clearValidationState();
    setSettings((currentSettings) =>
      currentSettings
        ? { ...currentSettings, ...nextSettings }
        : currentSettings,
    );
  };

  const handleSymbolsChange = (value: string) => {
    clearValidationState();
    setSymbols(value);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();

    if (!settings) {
      return;
    }

    const parsedSymbols = parseSymbols(symbols);
    if (parsedSymbols.length === 0) {
      setSaved(false);
      setError("Add at least one trading symbol before saving settings.");
      return;
    }

    const nextSettings: UserSettingsUpdate = {
      symbols: parsedSymbols,
      timeframe: settings.timeframe,
      balance: settings.balance,
      risk_per_trade: settings.risk_per_trade,
      grid_levels: settings.grid_levels,
      grid_step_pct: settings.grid_step_pct,
      martingale_factor: settings.martingale_factor,
      enable_trading: settings.enable_trading,
      email_notifications: settings.email_notifications,
    };

    setIsSaving(true);
    try {
      const response = await settingsAPI.updateUserSettings(nextSettings);
      setSettings(response.data);
      setSymbols(response.data.symbols.join(", "));
      setError(null);
      setSaved(true);
    } catch (saveError) {
      console.error("Failed to save settings:", saveError);
      setSaved(false);
      setError(
        "Failed to save settings. Please check your values and try again.",
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleSendTestNotification = async () => {
    setIsTestingNotification(true);
    setNotificationStatus(null);

    try {
      const response = await notificationsAPI.sendTest();
      const recipients = response.data.recipients.join(", ");
      if (response.data.status === "sent") {
        setNotificationStatus(`Test notification sent to ${recipients}.`);
      } else {
        setNotificationStatus(
          response.data.error
            ? `Notification test failed: ${response.data.error}`
            : "Notification test failed.",
        );
      }
    } catch (testError) {
      console.error("Failed to send test notification:", testError);
      setNotificationStatus(
        "Failed to send test notification. Check SMTP settings and try again.",
      );
    } finally {
      setIsTestingNotification(false);
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
          Configure MVP defaults for symbols, timeframe, risk, balance, and
          notifications.
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
            onChange={(event) => handleSymbolsChange(event.target.value)}
            placeholder="EURUSD, GBPUSD"
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none focus:border-brand-500"
          />
          <span className="mt-2 block text-xs text-slate-500">
            Defaults are loaded automatically for new users and can be edited here.
          </span>
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <NumberField
            label="Initial Balance"
            value={settings.balance}
            min="0"
            onChange={(value) => updateSettings({ balance: value })}
          />
          <NumberField
            label="Risk Per Trade (%)"
            value={settings.risk_per_trade * 100}
            min="0.1"
            max="20"
            step="0.1"
            onChange={(value) =>
              updateSettings({ risk_per_trade: value / 100 })
            }
          />
          <NumberField
            label="Grid Levels"
            value={settings.grid_levels}
            min="1"
            max="100"
            onChange={(value) => updateSettings({ grid_levels: value })}
          />
          <NumberField
            label="Grid Step (%)"
            value={settings.grid_step_pct * 100}
            min="0.01"
            max="20"
            step="0.1"
            onChange={(value) => updateSettings({ grid_step_pct: value / 100 })}
          />
          <NumberField
            label="Martingale Factor"
            value={settings.martingale_factor}
            min="1"
            max="10"
            step="0.1"
            onChange={(value) => updateSettings({ martingale_factor: value })}
          />
          <label className="block">
            <span className="text-sm text-slate-300">Timeframe</span>
            <select
              value={settings.timeframe}
              onChange={(event) =>
                updateSettings({
                  timeframe: event.target.value as SettingsTimeframe,
                })
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

        {notificationStatus && (
          <p className="rounded-lg bg-sky-500/10 px-3 py-2 text-sm text-sky-300">
            {notificationStatus}
          </p>
        )}

        <div className="flex flex-col gap-3 md:flex-row">
          <button
            type="submit"
            disabled={isSaving}
            className="w-full rounded-xl bg-brand-600 px-5 py-3 font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50 md:w-auto"
          >
            {isSaving ? "Saving..." : "Save Settings"}
          </button>
          <button
            type="button"
            onClick={handleSendTestNotification}
            disabled={isTestingNotification || !settings.email_notifications}
            className="w-full rounded-xl border border-slate-700 px-5 py-3 font-semibold text-slate-100 hover:border-brand-500 disabled:cursor-not-allowed disabled:opacity-50 md:w-auto"
          >
            {isTestingNotification ? "Sending test..." : "Send Test Email"}
          </button>
        </div>
      </form>
    </div>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step = "1",
  onChange,
}: {
  label: string;
  value: number;
  min?: string;
  max?: string;
  step?: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <span className="text-sm text-slate-300">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
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
