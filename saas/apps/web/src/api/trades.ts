import client from './client';
import type { Trade, TradeCloseRequest, TradeOpenRequest } from '../types';

export const tradesAPI = {
  getOpen: () => client.get<Trade[]>('/trades/open'),
  getClosed: (limit = 50) => client.get<Trade[]>('/trades/closed', { params: { limit } }),
  openTrade: (trade: TradeOpenRequest) => client.post<Trade>('/trades/open', trade),
  closeTrade: (tradeId: number, tradeClose: TradeCloseRequest) =>
    client.post<Trade>(`/trades/close/${tradeId}`, tradeClose),
};
