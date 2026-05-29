import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { User } from '../types';

const authAPIMocks = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}));

vi.mock('../api/auth', () => ({
  authAPI: authAPIMocks,
}));

function createMemoryStorage(): Storage {
  const store = new Map<string, string>();

  return {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key: string) => store.get(key) ?? null,
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(key);
    },
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
  };
}

const user: User = {
  id: 1,
  email: 'alice@example.com',
  username: 'alice',
  is_active: true,
  created_at: '2026-05-29T00:00:00Z',
};

async function loadAuthStore() {
  vi.resetModules();
  const { useAuthStore } = await import('./authStore');
  return useAuthStore;
}

describe('useAuthStore', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', createMemoryStorage());
    vi.clearAllMocks();
  });

  it('stores a successful login token and then loads the current user', async () => {
    const useAuthStore = await loadAuthStore();
    authAPIMocks.login.mockResolvedValue({ data: { access_token: 'token-123', token_type: 'bearer' } });
    authAPIMocks.getCurrentUser.mockResolvedValue({ data: user });

    await useAuthStore.getState().login('alice', 'secret-password');

    expect(authAPIMocks.login).toHaveBeenCalledWith('alice', 'secret-password');
    expect(authAPIMocks.getCurrentUser).toHaveBeenCalledOnce();
    expect(localStorage.getItem('access_token')).toBe('token-123');
    expect(localStorage.getItem('user')).toBe(JSON.stringify(user));
    expect(useAuthStore.getState()).toMatchObject({ token: 'token-123', user, isLoading: false, error: null });
  });

  it('sets the login error and skips current-user loading when login fails', async () => {
    const useAuthStore = await loadAuthStore();
    authAPIMocks.login.mockRejectedValue(new Error('invalid credentials'));

    await expect(useAuthStore.getState().login('alice', 'wrong-password')).rejects.toThrow('invalid credentials');

    expect(authAPIMocks.getCurrentUser).not.toHaveBeenCalled();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(useAuthStore.getState()).toMatchObject({
      error: 'Unable to sign in with those credentials.',
      isLoading: false,
    });
  });

  it('loads the current user with an existing stored token', async () => {
    localStorage.setItem('access_token', 'stored-token');
    const useAuthStore = await loadAuthStore();
    authAPIMocks.getCurrentUser.mockResolvedValue({ data: user });

    await useAuthStore.getState().loadCurrentUser();

    expect(authAPIMocks.getCurrentUser).toHaveBeenCalledOnce();
    expect(localStorage.getItem('user')).toBe(JSON.stringify(user));
    expect(useAuthStore.getState()).toMatchObject({ token: 'stored-token', user, isLoading: false });
  });
});
