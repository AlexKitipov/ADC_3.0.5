import client from './client';
import { User } from '../types';

export const authAPI = {
  register: (email: string, username: string, password: string) =>
    client.post<User>('/auth/register', {
      email,
      username,
      password,
    }),

  login: (username: string, password: string) =>
    client.post<{ access_token: string; token_type: string }>('/auth/login', null, {
      params: { username, password },
    }),

  getCurrentUser: () => client.get<User>('/auth/me'),
};
