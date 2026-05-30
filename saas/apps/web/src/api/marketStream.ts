import type { MarketTick } from '../types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export type MarketStreamEventHandlers = {
  onTick: (tick: MarketTick) => void;
  onOpen?: () => void;
  onError?: (error: Event) => void;
};

export function getMarketStreamUrl(symbol: string, interval = 1): string {
  const baseUrl = API_URL.replace(/\/$/, '');
  const url = new URL(`${baseUrl}/market-stream/${encodeURIComponent(symbol)}`);
  url.searchParams.set('interval', interval.toString());
  return url.toString();
}

export function subscribeToMarketStream(
  symbol: string,
  handlers: MarketStreamEventHandlers,
  interval = 1,
): EventSource {
  const source = new EventSource(getMarketStreamUrl(symbol, interval));

  source.addEventListener('connected', () => handlers.onOpen?.());
  source.addEventListener('tick', (event) => {
    const message = event as MessageEvent<string>;
    handlers.onTick(JSON.parse(message.data) as MarketTick);
  });
  source.onerror = (error) => handlers.onError?.(error);

  return source;
}
