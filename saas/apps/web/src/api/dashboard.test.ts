import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { dashboardAPI } from './dashboard';

type DashboardResponse = Awaited<ReturnType<typeof dashboardAPI.getStats>>;

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
  },
}));

describe('dashboardAPI', () => {
  it('requests stats and dashboard curve endpoints with days params', async () => {
    const mockedGet = vi.mocked(client.get);
    mockedGet.mockResolvedValue({ data: {} } as DashboardResponse);

    await dashboardAPI.getStats();
    await dashboardAPI.getEquityCurve(14);
    await dashboardAPI.getDrawdownCurve(14);

    expect(mockedGet).toHaveBeenNthCalledWith(1, '/dashboard/stats');
    expect(mockedGet).toHaveBeenNthCalledWith(2, '/dashboard/equity-curve', {
      params: { days: 14 },
    });
    expect(mockedGet).toHaveBeenNthCalledWith(3, '/dashboard/drawdown-curve', {
      params: { days: 14 },
    });
  });
});
