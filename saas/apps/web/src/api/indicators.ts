import client from './client';
import type {
  IndicatorCalculationRequest,
  IndicatorCalculationResponse,
} from '../types';

export const indicatorsAPI = {
  calculate: (payload: IndicatorCalculationRequest) =>
    client.post<IndicatorCalculationResponse>('/indicators/calculate', payload),
};
