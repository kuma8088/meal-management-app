/**
 * 目標管理API
 */

import { apiClient } from './client';
import type { Goal, CreateGoalRequest } from '../types/api';

/**
 * 目標を作成
 */
export const createGoal = async (data: CreateGoalRequest): Promise<Goal> => {
  const response = await apiClient.post<Goal>('/goals', data);
  return response.data;
};

/**
 * ユーザーの目標一覧を取得
 */
export const getGoals = async (userId: string): Promise<Goal[]> => {
  const response = await apiClient.get<Goal[]>(`/users/${userId}/goals`);
  return response.data;
};

/**
 * 特定の目標を取得
 */
export const getGoal = async (goalId: string): Promise<Goal> => {
  const response = await apiClient.get<Goal>(`/goals/${goalId}`);
  return response.data;
};
