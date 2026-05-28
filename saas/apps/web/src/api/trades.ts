import client from './client';
import { Trade } from '../types';

export const tradesAPI = {
  getOpen: () => client.get<Trade[]>('/trades/open'),
  getClosed: (limit = 50) => client.get<Trade[]>('/trades/closed', { params: { limit } }),
  openTrade: (symbol: string, entry_price: number) =>
    client.post<Trade>('/trades/open', { symbol, entry_price }),
  closeTrade: (trade_id: number, exit_price: number) =>
    client.post<Trade>(`/trades/close/${trade_id}`, null, { params: { exit_price } }),
};
