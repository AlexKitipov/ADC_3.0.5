import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { lstmAPI } from './lstm';
import type { LSTMGenerateRequest, LSTMTrainRequest, OHLCVRow } from '../types';

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const rows: OHLCVRow[] = [
  {
    timestamp: '2024-01-01T00:00:00Z',
    symbol: 'MSFT',
    open: 100,
    high: 101,
    low: 99,
    close: 100.5,
    volume: 1000,
  },
];

describe('lstmAPI', () => {
  it('posts standalone LSTM training requests', async () => {
    const mockedPost = vi.mocked(client.post);
    const payload: LSTMTrainRequest = {
      rows,
      features: ['Open', 'High', 'Low', 'Close', 'Volume'],
      sequence_length: 2,
      epochs: 1,
      batch_size: 2,
    };
    mockedPost.mockResolvedValue({ data: { id: 'job-1' } });

    await lstmAPI.train(payload);

    expect(mockedPost).toHaveBeenCalledWith('/lstm/train', payload);
  });

  it('posts generation requests and fetches job status', async () => {
    const mockedGet = vi.mocked(client.get);
    const mockedPost = vi.mocked(client.post);
    const payload: LSTMGenerateRequest = { job_id: 'job-1', num_steps: 5 };
    mockedPost.mockResolvedValue({ data: { rows: [] } });
    mockedGet.mockResolvedValue({ data: { id: 'job-1' } });

    await lstmAPI.generate(payload);
    await lstmAPI.getJob('job-1');

    expect(mockedPost).toHaveBeenCalledWith('/lstm/generate', payload);
    expect(mockedGet).toHaveBeenCalledWith('/lstm/jobs/job-1');
  });
});
