import client from './client';
import type { Signal, SignalGenerateRequest, SignalGenerateResponse } from '../types';

export const signalsAPI = {
  generate: (payload?: SignalGenerateRequest) =>
    client.post<SignalGenerateResponse>('/signals/generate', payload ?? {}),
  getLatest: (limit = 10) => client.get<Signal[]>('/signals/latest', { params: { limit } }),
  getBySymbol: (symbol: string, limit = 20) =>
    client.get<Signal[]>(`/signals/by-symbol/${symbol}`, { params: { limit } }),
};
