import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { tradesAPI } from '../api/trades';
import { TradesContent, closeSimpleTrade, loadTrades, openSimpleTrade } from './TradesPage';

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
  status: 'open',
};

const closedTrade = {
  ...openTrade,
  exit_price: 112,
  exit_time: '2026-05-29T13:00:00',
  pnl: 12,
  pnl_percent: 12,
  status: 'closed',
};

describe('TradesPage helpers', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('loads open and closed trades from the SaaS trade history endpoints', async () => {
    vi.mocked(tradesAPI.getOpen).mockResolvedValue({ data: [openTrade] } as OpenTradesResponse);
    vi.mocked(tradesAPI.getClosed).mockResolvedValue({ data: [closedTrade] } as OpenTradesResponse);

    await expect(loadTrades()).resolves.toEqual({ openTrades: [openTrade], closedTrades: [closedTrade] });
    expect(tradesAPI.getOpen).toHaveBeenCalledWith();
    expect(tradesAPI.getClosed).toHaveBeenCalledWith();
  });

  it('reports a friendly load error when trade history cannot be fetched', async () => {
    vi.mocked(tradesAPI.getOpen).mockRejectedValue(new Error('unavailable'));
    vi.mocked(tradesAPI.getClosed).mockResolvedValue({ data: [] } as OpenTradesResponse);

    await expect(loadTrades()).rejects.toThrow('Trade history could not be loaded.');
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


describe('TradesContent UI smoke', () => {
  const noop = () => undefined;

  it('renders empty open-trade lifecycle guidance', () => {
    const html = renderToStaticMarkup(
      createElement(TradesContent, {
        activeTab: 'open',
        closedTrades: [],
        entryPrice: '',
        errorMessage: null,
        exitPrices: {},
        isSaving: false,
        onActiveTabChange: noop,
        onCloseTrade: noop,
        onEntryPriceChange: noop,
        onExitPriceChange: noop,
        onOpenTrade: noop,
        onRefreshTrades: noop,
        onSymbolChange: noop,
        openTrades: [],
        successMessage: null,
        symbol: '',
      }),
    );

    expect(html).toContain('Open a mock trade');
    expect(html).toContain('No open trades. Open a mock trade to start the lifecycle.');
    expect(html).toContain('Open (0)');
    expect(html).toContain('Closed (0)');
  });

  it('renders open and closed trade lifecycle states from mocked API data', () => {
    const openHtml = renderToStaticMarkup(
      createElement(TradesContent, {
        activeTab: 'open',
        closedTrades: [closedTrade],
        entryPrice: '',
        errorMessage: null,
        exitPrices: { [openTrade.id]: '112' },
        isSaving: false,
        onActiveTabChange: noop,
        onCloseTrade: noop,
        onEntryPriceChange: noop,
        onExitPriceChange: noop,
        onOpenTrade: noop,
        onRefreshTrades: noop,
        onSymbolChange: noop,
        openTrades: [openTrade],
        successMessage: 'BTCUSD trade opened at $100.00.',
        symbol: '',
      }),
    );

    const closedHtml = renderToStaticMarkup(
      createElement(TradesContent, {
        activeTab: 'closed',
        closedTrades: [closedTrade],
        entryPrice: '',
        errorMessage: null,
        exitPrices: {},
        isSaving: false,
        onActiveTabChange: noop,
        onCloseTrade: noop,
        onEntryPriceChange: noop,
        onExitPriceChange: noop,
        onOpenTrade: noop,
        onRefreshTrades: noop,
        onSymbolChange: noop,
        openTrades: [],
        successMessage: 'BTCUSD trade closed with $12.00 (12.00%).',
        symbol: '',
      }),
    );

    expect(openHtml).toContain('Close trade');
    expect(openHtml).toContain('BTCUSD trade opened');
    expect(closedHtml).toContain('BTCUSD trade closed');
    expect(closedHtml).toContain('$12.00 (12.00%)');
  });
});
