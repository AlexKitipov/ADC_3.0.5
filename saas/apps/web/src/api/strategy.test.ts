import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { strategyAPI } from './strategy';

type StrategyParametersResponse = Awaited<ReturnType<typeof strategyAPI.getParameters>>;

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
  },
}));

describe('strategyAPI', () => {
  it('requests strategy parameter metadata endpoint', async () => {
    const mockedGet = vi.mocked(client.get);
    mockedGet.mockResolvedValue({ data: [] } as StrategyParametersResponse);

    await strategyAPI.getParameters();

    expect(mockedGet).toHaveBeenCalledWith('/strategy/parameters');
  });
});
