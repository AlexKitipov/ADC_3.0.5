import { create } from 'zustand';
import { authAPI } from '../api/auth';
import { User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  loadCurrentUser: () => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

const getInitialToken = () => localStorage.getItem('access_token');

const getInitialUser = () => {
  const storedUser = localStorage.getItem('user');
  if (!storedUser) {
    return null;
  }

  return JSON.parse(storedUser) as User;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: getInitialUser(),
  token: getInitialToken(),
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await authAPI.login(username, password);
      localStorage.setItem('access_token', data.access_token);
      const userResponse = await authAPI.getCurrentUser();
      localStorage.setItem('user', JSON.stringify(userResponse.data));
      set({ token: data.access_token, user: userResponse.data, isLoading: false });
    } catch (error) {
      set({ error: 'Unable to sign in with those credentials.', isLoading: false });
      throw error;
    }
  },

  register: async (email, username, password) => {
    set({ isLoading: true, error: null });
    try {
      await authAPI.register({ email, username, password });
      const { data } = await authAPI.login(username, password);
      localStorage.setItem('access_token', data.access_token);
      const userResponse = await authAPI.getCurrentUser();
      localStorage.setItem('user', JSON.stringify(userResponse.data));
      set({ token: data.access_token, user: userResponse.data, isLoading: false });
    } catch (error) {
      set({ error: 'Unable to create an account.', isLoading: false });
      throw error;
    }
  },

  loadCurrentUser: async () => {
    const token = getInitialToken();
    if (!token) {
      set({ user: null, token: null, isLoading: false });
      return;
    }

    set({ isLoading: true, error: null, token });
    try {
      const { data } = await authAPI.getCurrentUser();
      localStorage.setItem('user', JSON.stringify(data));
      set({ user: data, isLoading: false });
    } catch (error) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      set({ user: null, token: null, isLoading: false, error: 'Session expired.' });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    set({ user: null, token: null, error: null });
  },

  setUser: (user) => {
    localStorage.setItem('user', JSON.stringify(user));
    set({ user });
  },
}));
