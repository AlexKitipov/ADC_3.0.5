import client from './client';
import { Trade } from '../types';

export const tradesAPI = {
  getOpen: () => client.get<Trade[]>('/trades/open'),
  getClosed: (limit = 50) => client.get<Trade[]>('/trades/closed', { params: { limit } }),
};
