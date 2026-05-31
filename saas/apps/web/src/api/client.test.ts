import { beforeEach, describe, expect, it, vi } from 'vitest';

const axiosMock = vi.hoisted(() => {
  const requestUse = vi.fn();
  const client = {
    interceptors: {
      request: {
        use: requestUse,
      },
    },
  };

  return {
    client,
    create: vi.fn(() => client),
    requestUse,
  };
});

vi.mock('axios', () => ({
  default: {
    create: axiosMock.create,
  },
}));

describe('API client bearer interceptor', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('creates the axios client with the MVP API base URL', async () => {
    const { default: client } = await import('./client');

    expect(client).toBe(axiosMock.client);
    expect(axiosMock.create).toHaveBeenCalledWith({
      baseURL: 'http://localhost:8000/api/v1',
    });
  });

  it('adds a bearer authorization header when an access token exists', async () => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => 'abc123'),
    });

    await import('./client');
    const interceptor = axiosMock.requestUse.mock.calls[0][0];
    const config = { headers: {} as Record<string, string> };

    expect(interceptor(config)).toEqual({
      headers: { Authorization: 'Bearer abc123' },
    });
    expect(localStorage.getItem).toHaveBeenCalledWith('access_token');
  });

  it('leaves request headers untouched when no access token exists', async () => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
    });

    await import('./client');
    const interceptor = axiosMock.requestUse.mock.calls[0][0];
    const config = { headers: { Accept: 'application/json' } };

    expect(interceptor(config)).toEqual({
      headers: { Accept: 'application/json' },
    });
  });
});
