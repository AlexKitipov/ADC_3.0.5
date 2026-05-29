import client from './client';
import type { MarketDataRequest, MarketDataResponse } from '../types';

export const marketDataAPI = {
  getOHLCV: (params: MarketDataRequest) =>
    client.get<MarketDataResponse>('/market-data/ohlcv', { params }),
};
