import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signalsAPI } from '../api/signals';
import {
  buildSignalExplanation,
  describeMacd,
  describeRsi,
  getSignalActionClass,
  loadSignals,
} from './SignalsPage';

type SignalsResponse = Awaited<ReturnType<typeof signalsAPI.getLatest>>;

vi.mock('../api/signals', () => ({
  signalsAPI: {
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
});
