import client from './client';
import type { StrategyParameterSpec } from '../types';

export const strategyAPI = {
  getParameters: () => client.get<StrategyParameterSpec[]>('/strategy/parameters'),
};
