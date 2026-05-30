import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { tradeJournalAPI } from './tradeJournal';

type JournalResponse = Awaited<ReturnType<typeof tradeJournalAPI.getJournal>>;

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('tradeJournalAPI', () => {
  it('requests journal browse and export endpoints', async () => {
    const mockedGet = vi.mocked(client.get);
    mockedGet.mockResolvedValue({ data: { entries: [] } } as JournalResponse);

    await tradeJournalAPI.getJournal();
    await tradeJournalAPI.exportJournal();
    await tradeJournalAPI.downloadExport();

    expect(mockedGet).toHaveBeenNthCalledWith(1, '/trade-journal');
    expect(mockedGet).toHaveBeenNthCalledWith(2, '/trade-journal/export');
    expect(mockedGet).toHaveBeenNthCalledWith(3, '/trade-journal/export', { params: { download: true }, responseType: 'blob' });
  });

  it('imports artifacts as multipart data', async () => {
    const mockedPost = vi.mocked(client.post);
    const formData = new FormData();

    await tradeJournalAPI.importArtifact(formData, 'trades');

    expect(mockedPost).toHaveBeenCalledWith('/trade-journal/import', formData, {
      params: { artifact_type: 'trades' },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  });
});
