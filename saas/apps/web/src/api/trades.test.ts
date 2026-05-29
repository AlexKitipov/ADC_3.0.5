import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { tradesAPI } from './trades';

type TradesResponse = Awaited<ReturnType<typeof tradesAPI.getOpen>>;
type TradeResponse = Awaited<ReturnType<typeof tradesAPI.openTrade>>;

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('tradesAPI', () => {
  it('requests open and closed trade collection endpoints', async () => {
    const mockedGet = vi.mocked(client.get);
    mockedGet.mockResolvedValue({ data: [] } as TradesResponse);

    await tradesAPI.getOpen();
    await tradesAPI.getClosed(25);

    expect(mockedGet).toHaveBeenNthCalledWith(1, '/trades/open');
    expect(mockedGet).toHaveBeenNthCalledWith(2, '/trades/closed', { params: { limit: 25 } });
  });

  it('sends JSON request bodies for simple open and close actions', async () => {
    const mockedPost = vi.mocked(client.post);
    mockedPost.mockResolvedValue({ data: {} } as TradeResponse);

    await tradesAPI.openTrade({ symbol: 'BTCUSD', entry_price: 100 });
    await tradesAPI.closeTrade(7, { exit_price: 112 });

    expect(mockedPost).toHaveBeenNthCalledWith(1, '/trades/open', { symbol: 'BTCUSD', entry_price: 100 });
    expect(mockedPost).toHaveBeenNthCalledWith(2, '/trades/close/7', { exit_price: 112 });
  });
});
