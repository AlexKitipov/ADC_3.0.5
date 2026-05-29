import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { marketDataAPI } from './marketData';

type MarketDataResponse = Awaited<ReturnType<typeof marketDataAPI.getOHLCV>>;

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
  },
}));

describe('marketDataAPI', () => {
  it('requests OHLCV rows with preview query params', async () => {
    const mockedGet = vi.mocked(client.get);
    mockedGet.mockResolvedValue({ data: { rows: [] } } as MarketDataResponse);

    await marketDataAPI.getOHLCV({
      symbol: 'AAPL',
      timeframe: '1d',
      start_date: '2026-01-01',
      end_date: '2026-01-31',
    });

    expect(mockedGet).toHaveBeenCalledWith('/market-data/ohlcv', {
      params: {
        symbol: 'AAPL',
        timeframe: '1d',
        start_date: '2026-01-01',
        end_date: '2026-01-31',
      },
    });
  });
});
