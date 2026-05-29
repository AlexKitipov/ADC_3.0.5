import client from './client';
import { DashboardStats, DrawdownPoint, EquityPoint } from '../types';

export const dashboardAPI = {
  getStats: () => client.get<DashboardStats>('/dashboard/stats'),
  getEquityCurve: (days = 30) =>
    client.get<EquityPoint[]>('/dashboard/equity-curve', { params: { days } }),
  getDrawdownCurve: (days = 30) =>
    client.get<DrawdownPoint[]>('/dashboard/drawdown-curve', {
      params: { days },
    }),
};
