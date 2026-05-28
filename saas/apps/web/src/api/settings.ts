import client from './client';
import { UserSettings } from '../types';

export const settingsAPI = {
  getUserSettings: () => client.get<UserSettings | null>('/settings/user-settings'),
  updateUserSettings: (settings: UserSettings) =>
    client.put<{ message: string }>('/settings/user-settings', settings),
};
