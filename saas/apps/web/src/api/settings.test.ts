import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { settingsAPI } from './settings';
import { UserSettingsUpdate } from '../types';

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

describe('settingsAPI', () => {
  it('uses the stable MVP user-settings endpoints', async () => {
    const mockedGet = vi.mocked(client.get);
    const mockedPut = vi.mocked(client.put);
    const payload: UserSettingsUpdate = {
      symbols: ['EURUSD', 'GBPUSD'],
      timeframe: '1d',
      balance: 10000,
      risk_per_trade: 0.02,
      grid_levels: 3,
      grid_step_pct: 0.005,
      martingale_factor: 1.1,
      enable_trading: false,
      email_notifications: true,
    };

    mockedGet.mockResolvedValue({ data: { id: 1, ...payload } });
    mockedPut.mockResolvedValue({ data: { id: 1, ...payload } });

    await settingsAPI.getUserSettings();
    await settingsAPI.updateUserSettings(payload);

    expect(mockedGet).toHaveBeenCalledWith('/settings/user-settings');
    expect(mockedPut).toHaveBeenCalledWith('/settings/user-settings', payload);
  });
});
