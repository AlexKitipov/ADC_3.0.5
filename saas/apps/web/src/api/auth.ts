import client from './client';
import type { Token, User, UserCreate } from '../types';

export const authAPI = {
  register: (payload: UserCreate) => client.post<User>('/auth/register', payload),

  login: (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.set('username', username);
    formData.set('password', password);

    return client.post<Token>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },

  getCurrentUser: () => client.get<User>('/auth/me'),
};
