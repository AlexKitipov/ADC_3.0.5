import client from './client';
import type { SimulationArtifact, SimulationRequest, SimulationRun } from '../types';

export const simulationsAPI = {
  create: (payload: SimulationRequest) => client.post<SimulationRun>('/simulations', payload),
  get: (simulationId: string) => client.get<SimulationRun>(`/simulations/${simulationId}`),
  getArtifacts: (simulationId: string) =>
    client.get<SimulationArtifact[]>(`/simulations/${simulationId}/artifacts`),
};
