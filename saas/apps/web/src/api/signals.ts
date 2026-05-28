import client from './client';
import { Signal } from '../types';

export const signalsAPI = {
  getLatest: (limit = 10) => client.get<Signal[]>('/signals/latest', { params: { limit } }),
  getBySymbol: (symbol: string, limit = 20) =>
    client.get<Signal[]>(`/signals/by-symbol/${symbol}`, { params: { limit } }),
};
