import { describe, expect, it, vi } from 'vitest';
import { getMarketStreamUrl, subscribeToMarketStream } from './marketStream';

type Listener = (event: MessageEvent<string>) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];
  readonly url: string;
  onerror: ((event: Event) => void) | null = null;
  private listeners = new Map<string, Listener>();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(event: string, listener: Listener) {
    this.listeners.set(event, listener);
  }

  close = vi.fn();

  emit(event: string, data: unknown) {
    this.listeners.get(event)?.({ data: JSON.stringify(data) } as MessageEvent<string>);
  }
}

describe('market stream API helpers', () => {
  it('builds an SSE URL from the configured API base', () => {
    const url = getMarketStreamUrl('EUR/USD', 2.5);

    expect(url).toBe('http://localhost:8000/api/v1/market-stream/EUR%2FUSD?interval=2.5');
  });

  it('subscribes to tick events with EventSource', () => {
    const originalEventSource = globalThis.EventSource;
    globalThis.EventSource = MockEventSource as unknown as typeof EventSource;
    const onTick = vi.fn();
    const onOpen = vi.fn();
    const onError = vi.fn();

    const source = subscribeToMarketStream('EURUSD', { onTick, onOpen, onError });
    const instance = MockEventSource.instances[MockEventSource.instances.length - 1];
    expect(instance?.url).toBe('http://localhost:8000/api/v1/market-stream/EURUSD?interval=1');

    instance?.emit('connected', { symbol: 'EURUSD' });
    instance?.emit('tick', {
      symbol: 'EURUSD',
      price: 1.1,
      bid: 1.09995,
      ask: 1.10005,
      timestamp: '2026-05-30T00:00:00Z',
    });
    instance?.onerror?.(new Event('error'));

    expect(source).toBe(instance);
    expect(onOpen).toHaveBeenCalledOnce();
    expect(onTick).toHaveBeenCalledWith({
      symbol: 'EURUSD',
      price: 1.1,
      bid: 1.09995,
      ask: 1.10005,
      timestamp: '2026-05-30T00:00:00Z',
    });
    expect(onError).toHaveBeenCalledOnce();
    globalThis.EventSource = originalEventSource;
  });
});
