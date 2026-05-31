import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { dashboardAPI } from '../api/dashboard';
import {
  DashboardContent,
  loadDashboardData,
  normalizeDashboardStats,
  shouldShowSignalCta,
} from './DashboardPage';

type StatsResponse = Awaited<ReturnType<typeof dashboardAPI.getStats>>;
type EquityResponse = Awaited<ReturnType<typeof dashboardAPI.getEquityCurve>>;
type DrawdownResponse = Awaited<
  ReturnType<typeof dashboardAPI.getDrawdownCurve>
>;

vi.mock('../api/dashboard', () => ({
  dashboardAPI: {
    getStats: vi.fn(),
    getEquityCurve: vi.fn(),
    getDrawdownCurve: vi.fn(),
  },
}));

describe('loadDashboardData', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('normalizes nullable stats to safe zero defaults for new users', () => {
    const stats = normalizeDashboardStats({
      total_balance: null,
      current_equity: null,
      max_drawdown: null,
      win_rate: null,
      total_trades: null,
      monthly_pnl: null,
    });

    expect(stats).toEqual({
      total_balance: 0,
      current_equity: 0,
      max_drawdown: 0,
      win_rate: 0,
      total_trades: 0,
      monthly_pnl: 0,
    });
    expect(shouldShowSignalCta(stats)).toBe(true);
  });

  it('hides the signal CTA after trades are present', () => {
    expect(
      shouldShowSignalCta({
        total_balance: 10000,
        current_equity: 10100,
        max_drawdown: 0.02,
        win_rate: 0.6,
        total_trades: 3,
        monthly_pnl: 100,
      }),
    ).toBe(false);
  });

  it('returns available dashboard data and warns about failed curve requests', async () => {
    const stats = {
      total_balance: 10000,
      current_equity: 10125.5,
      max_drawdown: 0.025,
      win_rate: 0.5,
      total_trades: 8,
      monthly_pnl: 125.5,
    };
    const equity = [
      {
        timestamp: '2026-05-28T12:00:00',
        equity: 10125.5,
        balance: 10000,
      },
    ];

    vi.mocked(dashboardAPI.getStats).mockResolvedValue({
      data: stats,
    } as StatsResponse);
    vi.mocked(dashboardAPI.getEquityCurve).mockResolvedValue({
      data: equity,
    } as EquityResponse);
    vi.mocked(dashboardAPI.getDrawdownCurve).mockRejectedValue(
      new Error('network'),
    );

    await expect(loadDashboardData(14)).resolves.toEqual({
      stats,
      equity,
      drawdown: [],
      warnings: ['Drawdown curve data could not be loaded.'],
    });
    expect(dashboardAPI.getEquityCurve).toHaveBeenCalledWith(14);
    expect(dashboardAPI.getDrawdownCurve).toHaveBeenCalledWith(14);
  });

  it('normalizes empty metric arrays and nullable curve values', async () => {
    vi.mocked(dashboardAPI.getStats).mockResolvedValue({
      data: {
        total_balance: null,
        current_equity: 10000,
        max_drawdown: null,
        win_rate: null,
        total_trades: 0,
        monthly_pnl: null,
      },
    } as StatsResponse);
    vi.mocked(dashboardAPI.getEquityCurve).mockResolvedValue({
      data: [
        {
          timestamp: '2026-05-28T12:00:00',
          equity: null,
          balance: null,
        },
      ],
    } as EquityResponse);
    vi.mocked(dashboardAPI.getDrawdownCurve).mockResolvedValue({
      data: [
        {
          timestamp: '2026-05-28T12:00:00',
          drawdown: null,
        },
      ],
    } as DrawdownResponse);

    await expect(loadDashboardData()).resolves.toMatchObject({
      stats: {
        total_balance: 0,
        current_equity: 10000,
        max_drawdown: 0,
        win_rate: 0,
        total_trades: 0,
        monthly_pnl: 0,
      },
      equity: [
        {
          timestamp: '2026-05-28T12:00:00',
          equity: 0,
          balance: 0,
        },
      ],
      drawdown: [
        {
          timestamp: '2026-05-28T12:00:00',
          drawdown: 0,
        },
      ],
      warnings: [],
    });
  });

  it('rejects when required stats fail', async () => {
    vi.mocked(dashboardAPI.getStats).mockRejectedValue(
      new Error('stats failed'),
    );
    vi.mocked(dashboardAPI.getEquityCurve).mockResolvedValue({
      data: [],
    } as EquityResponse);
    vi.mocked(dashboardAPI.getDrawdownCurve).mockResolvedValue({
      data: [],
    } as DrawdownResponse);

    await expect(loadDashboardData()).rejects.toThrow(
      'Dashboard stats were unavailable.',
    );
  });
});


describe('DashboardContent UI smoke', () => {
  it('renders onboarding and empty chart states for a new account dashboard', () => {
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(DashboardContent, {
          stats: {
            total_balance: 0,
            current_equity: 0,
            max_drawdown: 0,
            win_rate: 0,
            total_trades: 0,
            monthly_pnl: 0,
          },
          equity: [],
          drawdown: [],
          warnings: [],
        }),
      ),
    );

    expect(html).toContain('Build your first dashboard curve');
    expect(html).toContain('Generate signal');
    expect(html).toContain('No equity snapshots yet');
    expect(html).toContain('No drawdown snapshots yet');
  });
});
