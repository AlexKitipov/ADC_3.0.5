import { useEffect, useMemo, useState } from 'react';
import { subscribeToMarketStream } from '../api/marketStream';
import type { MarketTick } from '../types';

export type MarketStreamStatus =
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'closed';

export interface UseMarketStreamOptions {
  interval?: number;
  enabled?: boolean;
}

export interface UseMarketStreamResult {
  latestTick: MarketTick | null;
  ticks: MarketTick[];
  status: MarketStreamStatus;
  error: string | null;
}

const MAX_TICKS = 30;

export function useMarketStream(
  symbol: string,
  options: UseMarketStreamOptions = {},
): UseMarketStreamResult {
  const { interval = 1, enabled = true } = options;
  const normalizedSymbol = useMemo(() => symbol.trim().toUpperCase(), [symbol]);
  const [latestTick, setLatestTick] = useState<MarketTick | null>(null);
  const [ticks, setTicks] = useState<MarketTick[]>([]);
  const [status, setStatus] = useState<MarketStreamStatus>('connecting');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || normalizedSymbol.length === 0) {
      setStatus('closed');
      return undefined;
    }

    setStatus('connecting');
    setError(null);

    const source = subscribeToMarketStream(
      normalizedSymbol,
      {
        onOpen: () => {
          setStatus('connected');
          setError(null);
        },
        onTick: (tick) => {
          setLatestTick(tick);
          setTicks((currentTicks) =>
            [tick, ...currentTicks].slice(0, MAX_TICKS),
          );
          setStatus('connected');
          setError(null);
        },
        onError: () => {
          setStatus('reconnecting');
          setError('Market stream interrupted. Reconnecting automatically...');
        },
      },
      interval,
    );

    return () => {
      source.close();
      setStatus('closed');
    };
  }, [enabled, interval, normalizedSymbol]);

  return { latestTick, ticks, status, error };
}
