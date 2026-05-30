import { describe, expect, it, vi } from 'vitest';
import client from './client';
import { sessionsAPI } from './sessions';

type SessionResponse = Awaited<ReturnType<typeof sessionsAPI.createSession>>;
type EventsResponse = Awaited<ReturnType<typeof sessionsAPI.getEvents>>;

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('sessionsAPI', () => {
  it('requests session lifecycle endpoints', async () => {
    const mockedGet = vi.mocked(client.get);
    const mockedPost = vi.mocked(client.post);
    mockedGet.mockResolvedValue({ data: [] } as EventsResponse);
    mockedPost.mockResolvedValue({ data: {} } as SessionResponse);

    await sessionsAPI.createSession({ auto_start: true });
    await sessionsAPI.startSession('session-1');
    await sessionsAPI.stopSession('session-1');
    await sessionsAPI.getCurrent();
    await sessionsAPI.getEvents('session-1', 25);

    expect(mockedPost).toHaveBeenNthCalledWith(1, '/sessions', { auto_start: true });
    expect(mockedPost).toHaveBeenNthCalledWith(2, '/sessions/session-1/start');
    expect(mockedPost).toHaveBeenNthCalledWith(3, '/sessions/session-1/stop');
    expect(mockedGet).toHaveBeenNthCalledWith(1, '/sessions/current');
    expect(mockedGet).toHaveBeenNthCalledWith(2, '/sessions/session-1/events', { params: { limit: 25 } });
  });
});
