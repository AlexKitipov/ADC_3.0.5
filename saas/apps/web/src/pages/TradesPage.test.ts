import { beforeEach, describe, expect, it, vi } from 'vitest';
import { tradesAPI } from '../api/trades';
import { closeSimpleTrade, loadTrades, openSimpleTrade } from './TradesPage';

type OpenTradesResponse = Awaited<ReturnType<typeof tradesAPI.getOpen>>;
type TradeActionResponse = Awaited<ReturnType<typeof tradesAPI.openTrade>>;

vi.mock('../api/trades', () => ({
  tradesAPI: {
    getOpen: vi.fn(),
    getClosed: vi.fn(),
    openTrade: vi.fn(),
    closeTrade: vi.fn(),
  },
}));

const openTrade = {
  id: 1,
  symbol: 'BTCUSD',
  entry_price: 100,
  exit_price: null,
  entry_time: '2026-05-29T12:00:00',
  exit_time: null,
  pnl: null,
  pnl_percent: null,
  status: 'open' as const,
};

const closedTrade = {
  ...openTrade,
  exit_price: 112,
  exit_time: '2026-05-29T13:00:00',
  pnl: 12,
  pnl_percent: 12,
  status: 'closed' as const,
};

describe('TradesPage helpers', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('loads open and closed trades together', async () => {
    vi.mocked(tradesAPI.getOpen).mockResolvedValue({ data: [openTrade] } as OpenTradesResponse);
    vi.mocked(tradesAPI.getClosed).mockResolvedValue({ data: [closedTrade] } as OpenTradesResponse);

    await expect(loadTrades()).resolves.toEqual({ openTrades: [openTrade], closedTrades: [closedTrade] });
    expect(tradesAPI.getOpen).toHaveBeenCalledWith();
    expect(tradesAPI.getClosed).toHaveBeenCalledWith();
  });

  it('opens simple trades with normalized symbols and JSON payloads', async () => {
    vi.mocked(tradesAPI.openTrade).mockResolvedValue({ data: openTrade } as TradeActionResponse);

    await expect(openSimpleTrade(' btcusd ', 100)).resolves.toEqual(openTrade);
    expect(tradesAPI.openTrade).toHaveBeenCalledWith({ symbol: 'BTCUSD', entry_price: 100 });
  });

  it('closes simple trades with JSON payloads', async () => {
    vi.mocked(tradesAPI.closeTrade).mockResolvedValue({ data: closedTrade } as TradeActionResponse);

    await expect(closeSimpleTrade(1, 112)).resolves.toEqual(closedTrade);
    expect(tradesAPI.closeTrade).toHaveBeenCalledWith(1, { exit_price: 112 });
  });

  it('validates open and close action input before calling the API', async () => {
    await expect(openSimpleTrade('', 100)).rejects.toThrow('Symbol is required.');
    await expect(openSimpleTrade('BTCUSD', 0)).rejects.toThrow('Entry price must be greater than zero.');
    await expect(closeSimpleTrade(1, 0)).rejects.toThrow('Exit price must be greater than zero.');
    expect(tradesAPI.openTrade).not.toHaveBeenCalled();
    expect(tradesAPI.closeTrade).not.toHaveBeenCalled();
  });
});
