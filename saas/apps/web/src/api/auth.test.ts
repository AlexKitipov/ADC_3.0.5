import { beforeEach, describe, expect, it, vi } from 'vitest';
import client from './client';
import { authAPI } from './auth';

type LoginResponse = Awaited<ReturnType<typeof authAPI.login>>;

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('authAPI', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('posts login credentials as OAuth2 form data instead of query params', async () => {
    const mockedPost = vi.mocked(client.post);
    mockedPost.mockResolvedValue({ data: { access_token: 'token', token_type: 'bearer' } } as unknown as LoginResponse);

    await authAPI.login('alice', 'secret-password');

    expect(mockedPost).toHaveBeenCalledWith('/auth/login', expect.any(URLSearchParams), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    const formData = mockedPost.mock.calls[0][1] as URLSearchParams;
    expect(formData.get('username')).toBe('alice');
    expect(formData.get('password')).toBe('secret-password');
    expect(mockedPost.mock.calls[0][2]).not.toHaveProperty('params');
  });

  it('posts registration payloads and requests the current user endpoint', async () => {
    const mockedGet = vi.mocked(client.get);
    const mockedPost = vi.mocked(client.post);
    const userPayload = {
      email: 'alice@example.com',
      username: 'alice',
      password: 'secret-password',
    };
    const user = {
      id: 1,
      email: userPayload.email,
      username: userPayload.username,
      is_active: true,
      created_at: '2026-05-31T12:00:00Z',
    };

    mockedPost.mockResolvedValue({ data: user });
    mockedGet.mockResolvedValue({ data: user });

    await authAPI.register(userPayload);
    await authAPI.getCurrentUser();

    expect(mockedPost).toHaveBeenCalledWith('/auth/register', userPayload);
    expect(mockedGet).toHaveBeenCalledWith('/auth/me');
  });
});
