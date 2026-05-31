import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ordersAPI } from '../api/orders';
import { tradeJournalAPI } from '../api/tradeJournal';
import { tradesAPI } from '../api/trades';
import { closeManualOrder, closeSimpleTrade, loadTrades, openSimpleTrade, submitManualOrder } from './TradesPage';

type OpenTradesResponse = Awaited<ReturnType<typeof tradesAPI.getOpen>>;
type TradeActionResponse = Awaited<ReturnType<typeof tradesAPI.openTrade>>;
type OrderActionResponse = Awaited<ReturnType<typeof ordersAPI.createOrder>>;

vi.mock('../api/orders', () => ({
  ordersAPI: {
    getOpen: vi.fn(),
    getByTicket: vi.fn(),
    createOrder: vi.fn(),
    closeOrder: vi.fn(),
  },
}));

vi.mock('../api/trades', () => ({
  tradesAPI: {
    getOpen: vi.fn(),
    getClosed: vi.fn(),
    openTrade: vi.fn(),
    closeTrade: vi.fn(),
  },
}));

vi.mock('../api/tradeJournal', () => ({
  tradeJournalAPI: {
    getJournal: vi.fn(),
    exportJournal: vi.fn(),
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

const manualOrder = {
  ticket: 100000,
  symbol: 'EURUSD',
  order_type: 'BUY' as const,
  volume: 0.1,
  price: 1.0851,
  stop_loss: 1.084,
  take_profit: 1.087,
  slippage: 100,
  status: 'open',
  broker_result: { status: 'open', error_code: 0, message: 'Order accepted by broker.' },
  open_time: '2026-05-29T12:00:00',
  close_price: null,
  close_time: null,
};

const closedTrade = {
  ...openTrade,
  exit_price: 112,
  exit_time: '2026-05-29T13:00:00',
  pnl: 12,
  pnl_percent: 12,
  status: 'closed' as const,
};

const journal = {
  entries: [],
  artifacts: [],
  db_trade_count: 2,
  open_db_trade_count: 1,
  closed_db_trade_count: 1,
  relationships: {
    persisted_trade_rows: 'Persisted rows',
    broker_order_records: 'Broker orders',
    journal_artifacts: 'Journal artifacts',
  },
};

describe('TradesPage helpers', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('loads open and closed trades together', async () => {
    vi.mocked(tradesAPI.getOpen).mockResolvedValue({ data: [openTrade] } as OpenTradesResponse);
    vi.mocked(tradesAPI.getClosed).mockResolvedValue({ data: [closedTrade] } as OpenTradesResponse);
    vi.mocked(ordersAPI.getOpen).mockResolvedValue({ data: [manualOrder] } as Awaited<ReturnType<typeof ordersAPI.getOpen>>);
    vi.mocked(tradeJournalAPI.getJournal).mockResolvedValue({ data: journal } as Awaited<ReturnType<typeof tradeJournalAPI.getJournal>>);

    await expect(loadTrades()).resolves.toEqual({ openTrades: [openTrade], closedTrades: [closedTrade], openOrders: [manualOrder], journal });
    expect(tradesAPI.getOpen).toHaveBeenCalledWith();
    expect(tradesAPI.getClosed).toHaveBeenCalledWith();
    expect(ordersAPI.getOpen).toHaveBeenCalledWith();
    expect(tradeJournalAPI.getJournal).toHaveBeenCalledWith();
  });

  it('keeps trade history available when manual order history dependencies fail', async () => {
    vi.mocked(tradesAPI.getOpen).mockResolvedValue({ data: [openTrade] } as OpenTradesResponse);
    vi.mocked(tradesAPI.getClosed).mockResolvedValue({ data: [closedTrade] } as OpenTradesResponse);
    vi.mocked(ordersAPI.getOpen).mockRejectedValue(new Error('orders unavailable'));
    vi.mocked(tradeJournalAPI.getJournal).mockRejectedValue(new Error('journal unavailable'));

    await expect(loadTrades()).resolves.toMatchObject({
      openTrades: [openTrade],
      closedTrades: [closedTrade],
      openOrders: [],
      journal: { entries: [], artifacts: [] },
    });
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

  it('submits and closes manual orders with normalized payloads', async () => {
    vi.mocked(ordersAPI.createOrder).mockResolvedValue({ data: manualOrder } as OrderActionResponse);
    vi.mocked(ordersAPI.closeOrder).mockResolvedValue({ data: { ...manualOrder, status: 'closed' } } as OrderActionResponse);

    await expect(submitManualOrder(' eurusd ', 'BUY', 0.1, 1.0851, 1.084, 1.087, 100)).resolves.toEqual(manualOrder);
    await expect(closeManualOrder(100000, 1.085, 100)).resolves.toMatchObject({ status: 'closed' });

    expect(ordersAPI.createOrder).toHaveBeenCalledWith({
      symbol: 'EURUSD',
      order_type: 'BUY',
      volume: 0.1,
      price: 1.0851,
      stop_loss: 1.084,
      take_profit: 1.087,
      slippage: 100,
      comment: 'manual-order',
    });
    expect(ordersAPI.closeOrder).toHaveBeenCalledWith(100000, { price: 1.085, slippage: 100, exit_reason: 'manual-close' });
  });

  it('validates open and close action input before calling the API', async () => {
    await expect(openSimpleTrade('', 100)).rejects.toThrow('Symbol is required.');
    await expect(openSimpleTrade('BTCUSD', 0)).rejects.toThrow('Entry price must be greater than zero.');
    await expect(closeSimpleTrade(1, 0)).rejects.toThrow('Exit price must be greater than zero.');
    expect(tradesAPI.openTrade).not.toHaveBeenCalled();
    await expect(submitManualOrder('', 'BUY', 0.1, 1.0851, 0, 0, 100)).rejects.toThrow('Order symbol is required.');
    await expect(submitManualOrder('EURUSD', 'BUY', 0, 1.0851, 0, 0, 100)).rejects.toThrow('Order volume must be greater than zero.');
    await expect(closeManualOrder(100000, 0, 100)).rejects.toThrow('Close price must be greater than zero.');
    expect(tradesAPI.closeTrade).not.toHaveBeenCalled();
    expect(ordersAPI.createOrder).not.toHaveBeenCalled();
    expect(ordersAPI.closeOrder).not.toHaveBeenCalled();
  });
});
