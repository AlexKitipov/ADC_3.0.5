import client from './client';
import type { LSTMGenerateRequest, LSTMGenerationResult, LSTMJob, LSTMTrainRequest } from '../types';

export const lstmAPI = {
  train: (payload: LSTMTrainRequest) => client.post<LSTMJob>('/lstm/train', payload),
  generate: (payload: LSTMGenerateRequest) => client.post<LSTMGenerationResult>('/lstm/generate', payload),
  getJob: (jobId: string) => client.get<LSTMJob>(`/lstm/jobs/${jobId}`),
};
