import client from './client';
import { UserSettings, UserSettingsUpdate } from '../types';

export const settingsAPI = {
  getUserSettings: () => client.get<UserSettings>('/settings/user-settings'),
  updateUserSettings: (settings: UserSettingsUpdate) =>
    client.put<UserSettings>('/settings/user-settings', settings),
};
