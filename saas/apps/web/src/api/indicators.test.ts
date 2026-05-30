import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { indicatorsAPI } from './indicators';

type IndicatorsResponse = Awaited<ReturnType<typeof indicatorsAPI.calculate>>;

vi.mock('./client', () => ({
  default: {
    post: vi.fn(),
  },
}));

describe('indicatorsAPI', () => {
  it('posts stateless OHLCV rows to the indicator calculation endpoint', async () => {
    const mockedPost = vi.mocked(client.post);
    mockedPost.mockResolvedValue({ data: { rows: [] } } as IndicatorsResponse);

    const payload = {
      rows: [
        {
          timestamp: '2026-01-02T00:00:00',
          symbol: 'AAPL',
          open: 100,
          high: 102,
          low: 99,
          close: 101,
          volume: 1000,
        },
      ],
    };

    await indicatorsAPI.calculate(payload);

    expect(mockedPost).toHaveBeenCalledWith('/indicators/calculate', payload);
  });
});
