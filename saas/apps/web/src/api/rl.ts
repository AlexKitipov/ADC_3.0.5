import client from './client';
import type { RLModelArtifact, RLTrainingJob, RLTrainingRequest } from '../types';

export const rlAPI = {
  train: (payload: RLTrainingRequest) => client.post<RLTrainingJob>('/rl/train', payload),
  getJob: (jobId: string) => client.get<RLTrainingJob>(`/rl/jobs/${jobId}`),
  getModel: (modelId: string) => client.get<RLModelArtifact>(`/rl/models/${modelId}`),
};
