import { describe, expect, it, vi } from 'vitest';
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
});
