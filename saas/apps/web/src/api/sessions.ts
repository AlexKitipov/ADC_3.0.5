import client from './client';
import type { SessionEvent, TradingSessionCreate, TradingSessionState } from '../types';

export const sessionsAPI = {
  createSession: (payload: TradingSessionCreate = {}) => client.post<TradingSessionState>('/sessions', payload),
  getCurrent: () => client.get<TradingSessionState>('/sessions/current'),
  startSession: (sessionId: string) => client.post<TradingSessionState>(`/sessions/${sessionId}/start`),
  stopSession: (sessionId: string) => client.post<TradingSessionState>(`/sessions/${sessionId}/stop`),
  getEvents: (sessionId: string, limit = 100) => client.get<SessionEvent[]>(`/sessions/${sessionId}/events`, { params: { limit } }),
};
