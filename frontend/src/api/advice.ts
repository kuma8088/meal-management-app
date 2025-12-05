/**
 * AIアドバイスAPI
 */

import { apiClient } from './client';
import type { DailyAdvice, GetDailyAdviceRequest } from '../types/api';

/**
 * 本日の総評とアドバイスを取得
 */
export const getDailyAdvice = async (
  data: GetDailyAdviceRequest
): Promise<DailyAdvice> => {
  const response = await apiClient.post<DailyAdvice>('/advice/daily', data);
  return response.data;
};
