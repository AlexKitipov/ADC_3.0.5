import { beforeEach, describe, expect, it, vi } from 'vitest';
import client from './client';
import { signalsAPI } from './signals';

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('signalsAPI', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('requests latest and symbol-scoped signal endpoints', async () => {
    const mockedGet = vi.mocked(client.get);
    mockedGet.mockResolvedValue({ data: [] });

    await signalsAPI.getLatest(5);
    await signalsAPI.getBySymbol('EURUSD', 3);

    expect(mockedGet).toHaveBeenNthCalledWith(1, '/signals/latest', { params: { limit: 5 } });
    expect(mockedGet).toHaveBeenNthCalledWith(2, '/signals/by-symbol/EURUSD', { params: { limit: 3 } });
  });

  it('posts an empty generate payload when backend defaults should be used', async () => {
    const mockedPost = vi.mocked(client.post);
    mockedPost.mockResolvedValue({ data: {} });

    await signalsAPI.generate();

    expect(mockedPost).toHaveBeenCalledWith('/signals/generate', {});
  });

  it('posts generate overrides when callers provide symbol and timeframe', async () => {
    const mockedPost = vi.mocked(client.post);
    mockedPost.mockResolvedValue({ data: {} });

    await signalsAPI.generate({ symbol: 'GBPUSD', timeframe: '5min' });

    expect(mockedPost).toHaveBeenCalledWith('/signals/generate', {
      symbol: 'GBPUSD',
      timeframe: '5min',
    });
  });
});
