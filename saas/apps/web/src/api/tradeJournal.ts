import client from './client';
import type { TradeJournalExportMetadata, TradeJournalImportSummary, TradeJournalSummary } from '../types';

export const tradeJournalAPI = {
  getJournal: () => client.get<TradeJournalSummary>('/trade-journal'),
  getEntry: (entryId: string) => client.get(`/trade-journal/${entryId}`),
  importArtifact: (formData: FormData, artifactType = 'trades') =>
    client.post<TradeJournalImportSummary>('/trade-journal/import', formData, {
      params: { artifact_type: artifactType },
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  exportJournal: () => client.get<TradeJournalExportMetadata>('/trade-journal/export'),
  downloadExport: () => client.get<Blob>('/trade-journal/export', { params: { download: true }, responseType: 'blob' }),
};
