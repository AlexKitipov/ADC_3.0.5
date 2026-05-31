import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signalsAPI } from '../api/signals';
import {
  buildSignalExplanation,
  describeMacd,
  generateSignal,
  mergeGeneratedSignal,
  describeRsi,
  getSignalActionClass,
  loadSignals,
} from './SignalsPage';

type SignalsResponse = Awaited<ReturnType<typeof signalsAPI.getLatest>>;
type GenerateResponse = Awaited<ReturnType<typeof signalsAPI.generate>>;

vi.mock('../api/signals', () => ({
  signalsAPI: {
    generate: vi.fn(),
    getLatest: vi.fn(),
  },
}));

describe('SignalsPage helpers', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('uses configured styling for expected signal actions', () => {
    expect(getSignalActionClass('BUY')).toContain('text-emerald-300');
    expect(getSignalActionClass('SELL')).toContain('text-rose-300');
    expect(getSignalActionClass('HOLD')).toContain('text-amber-300');
  });

  it('uses fallback styling for unexpected signal actions', () => {
    expect(getSignalActionClass('STRONG_BUY')).toContain('text-slate-300');
    expect(getSignalActionClass('toString')).toContain('text-slate-300');
  });

  it('describes RSI and MACD regimes for signal explanations', () => {
    expect(describeRsi(75)).toContain('Overbought');
    expect(describeRsi(25)).toContain('Oversold');
    expect(describeRsi(50)).toContain('Neutral');
    expect(describeMacd(0.12)).toContain('Bullish');
    expect(describeMacd(-0.12)).toContain('Bearish');
    expect(describeMacd(0)).toContain('Flat');
  });

  it('builds explanation copy that clarifies stateless indicator calculations', () => {
    const explanation = buildSignalExplanation({
      id: 1,
      symbol: 'EURUSD',
      action: 'BUY',
      price: 1.085,
      rsi: 25,
      macd: 0.15,
      timestamp: '2026-05-29T12:00:00',
    });

    expect(explanation[0]).toContain('BUY signal for EURUSD');
    expect(explanation.join(' ')).toContain('stateless indicator set');
  });

  it('includes generator confidence and explanation when present', () => {
    const explanation = buildSignalExplanation({
      id: 1,
      symbol: 'EURUSD',
      action: 'BUY',
      price: 1.085,
      rsi: 25,
      macd: 0.15,
      timestamp: '2026-05-29T12:00:00',
      confidence: 0.87,
      explanation: 'RSI recovery with bullish MACD momentum.',
    });

    expect(explanation.join(' ')).toContain('Generator confidence: 87.0%');
    expect(explanation.join(' ')).toContain('RSI recovery');
  });

  it('loads latest signals with the requested limit', async () => {
    const signals = [
      {
        id: 1,
        symbol: 'EURUSD',
        action: 'BUY',
        price: 1.085,
        rsi: 44.2,
        macd: 0.15,
        timestamp: '2026-05-29T12:00:00',
      },
    ];
    vi.mocked(signalsAPI.getLatest).mockResolvedValue({
      data: signals,
    } as SignalsResponse);

    await expect(loadSignals(5)).resolves.toEqual(signals);
    expect(signalsAPI.getLatest).toHaveBeenCalledWith(5);
  });

  it('surfaces a stable error message when signal loading fails', async () => {
    vi.mocked(signalsAPI.getLatest).mockRejectedValue(new Error('network'));

    await expect(loadSignals()).rejects.toThrow('Signals could not be loaded.');
  });

  it('generates a signal and merges decision context into the returned signal', async () => {
    vi.mocked(signalsAPI.generate).mockResolvedValue({
      data: {
        signal: {
          id: 2,
          symbol: 'GBPUSD',
          action: 'SELL',
          price: 1.271,
          rsi: 72,
          macd: -0.05,
          timestamp: '2026-05-29T12:05:00',
        },
        decision: {
          symbol: 'GBPUSD',
          action: 'SELL',
          confidence: 0.78,
          explanation: 'Overbought RSI and negative MACD.',
          metadata: { timeframe: '5min' },
        },
      },
    } as GenerateResponse);

    await expect(generateSignal({ symbol: 'GBPUSD', timeframe: '5min' })).resolves.toMatchObject({
      id: 2,
      symbol: 'GBPUSD',
      confidence: 0.78,
      explanation: 'Overbought RSI and negative MACD.',
    });
    expect(signalsAPI.generate).toHaveBeenCalledWith({ symbol: 'GBPUSD', timeframe: '5min' });
  });

  it('surfaces a stable error message when signal generation fails', async () => {
    vi.mocked(signalsAPI.generate).mockRejectedValue(new Error('network'));

    await expect(generateSignal()).rejects.toThrow('Signal could not be generated.');
  });

  it('prepends generated signals without duplicating an existing id', () => {
    const existing = {
      id: 1,
      symbol: 'EURUSD',
      action: 'BUY' as const,
      price: 1.085,
      rsi: 44.2,
      macd: 0.15,
      timestamp: '2026-05-29T12:00:00',
    };
    const generated = { ...existing, price: 1.09, confidence: 0.66 };

    expect(mergeGeneratedSignal([existing], generated)).toEqual([generated]);
  });
});
