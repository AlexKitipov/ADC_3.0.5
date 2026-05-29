import client from './client';
import type { DashboardStats, DrawdownCurvePoint, EquityCurvePoint } from '../types';

export const dashboardAPI = {
  getStats: () => client.get<DashboardStats>('/dashboard/stats'),
  getEquityCurve: (days = 30) =>
    client.get<EquityCurvePoint[]>('/dashboard/equity-curve', { params: { days } }),
  getDrawdownCurve: (days = 30) =>
    client.get<DrawdownCurvePoint[]>('/dashboard/drawdown-curve', {
      params: { days },
    }),
};
