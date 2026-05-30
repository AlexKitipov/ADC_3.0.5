import client from './client';
import type { Order, OrderClose, OrderCreate } from '../types';

export const ordersAPI = {
  getOpen: () => client.get<Order[]>('/orders/open'),
  getByTicket: (ticket: number) => client.get<Order>(`/orders/${ticket}`),
  createOrder: (order: OrderCreate) => client.post<Order>('/orders', order),
  closeOrder: (ticket: number, orderClose: OrderClose) => client.post<Order>(`/orders/${ticket}/close`, orderClose),
};
