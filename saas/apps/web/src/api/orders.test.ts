import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { ordersAPI } from './orders';

type OrdersResponse = Awaited<ReturnType<typeof ordersAPI.getOpen>>;
type OrderResponse = Awaited<ReturnType<typeof ordersAPI.createOrder>>;

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('ordersAPI', () => {
  it('requests manual order collection and detail endpoints', async () => {
    const mockedGet = vi.mocked(client.get);
    mockedGet.mockResolvedValue({ data: [] } as OrdersResponse);

    await ordersAPI.getOpen();
    await ordersAPI.getByTicket(100000);

    expect(mockedGet).toHaveBeenNthCalledWith(1, '/orders/open');
    expect(mockedGet).toHaveBeenNthCalledWith(2, '/orders/100000');
  });

  it('sends JSON request bodies for manual order actions', async () => {
    const mockedPost = vi.mocked(client.post);
    mockedPost.mockResolvedValue({ data: {} } as OrderResponse);

    await ordersAPI.createOrder({ symbol: 'EURUSD', order_type: 'BUY', volume: 0.1, price: 1.0851 });
    await ordersAPI.closeOrder(100000, { price: 1.085, slippage: 100 });

    expect(mockedPost).toHaveBeenNthCalledWith(1, '/orders', { symbol: 'EURUSD', order_type: 'BUY', volume: 0.1, price: 1.0851 });
    expect(mockedPost).toHaveBeenNthCalledWith(2, '/orders/100000/close', { price: 1.085, slippage: 100 });
  });
});
