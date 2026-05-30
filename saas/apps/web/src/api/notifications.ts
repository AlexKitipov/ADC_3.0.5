import client from './client';
import {
  NotificationDeliveryResponse,
  NotificationTestRequest,
  SimulationResultsNotificationRequest,
} from '../types';

export const notificationsAPI = {
  sendTest: (request: NotificationTestRequest = {}) =>
    client.post<NotificationDeliveryResponse>('/notifications/test', request),
  sendSimulationResults: (request: SimulationResultsNotificationRequest) =>
    client.post<NotificationDeliveryResponse>(
      '/notifications/simulation-results',
      request,
    ),
};
