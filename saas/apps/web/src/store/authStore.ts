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
}

const getInitialToken = () => localStorage.getItem('access_token');

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: getInitialToken(),
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await authAPI.login(username, password);
      localStorage.setItem('access_token', data.access_token);
      const userResponse = await authAPI.getCurrentUser();
      set({ token: data.access_token, user: userResponse.data, isLoading: false });
    } catch (error) {
      set({ error: 'Unable to sign in with those credentials.', isLoading: false });
      throw error;
    }
  },

  register: async (email, username, password) => {
    set({ isLoading: true, error: null });
    try {
      await authAPI.register(email, username, password);
      const { data } = await authAPI.login(username, password);
      localStorage.setItem('access_token', data.access_token);
      const userResponse = await authAPI.getCurrentUser();
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
      set({ user: data, isLoading: false });
    } catch (error) {
      localStorage.removeItem('access_token');
      set({ user: null, token: null, isLoading: false, error: 'Session expired.' });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    set({ user: null, token: null, error: null });
  },
}));
