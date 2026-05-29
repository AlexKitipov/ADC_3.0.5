import client from './client';
import { User } from '../types';

export const authAPI = {
  register: (email: string, username: string, password: string) =>
    client.post<User>('/auth/register', {
      email,
      username,
      password,
    }),

  login: (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.set('username', username);
    formData.set('password', password);

    return client.post<{ access_token: string; token_type: string }>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },

  getCurrentUser: () => client.get<User>('/auth/me'),
};
