/**
 * 食事記録API
 */

import { apiClient } from './client';
import type {
  Meal,
  CreateMealRequest,
  UpdateMealRequest,
  GetMealsParams,
} from '../types/api';

/**
 * 食事記録を作成
 */
export const createMeal = async (data: CreateMealRequest): Promise<Meal> => {
  const response = await apiClient.post<Meal>('/meals', data);
  return response.data;
};

/**
 * 食事記録一覧を取得
 *
 * APIレスポンス形式: { meals: [...], count: N, has_more: bool }
 */
export const getMeals = async (params?: GetMealsParams): Promise<Meal[]> => {
  const response = await apiClient.get<{ meals: Meal[]; count: number; has_more: boolean }>('/meals', { params });
  return response.data.meals;
};

/**
 * 特定の食事記録を取得
 */
export const getMeal = async (mealId: string): Promise<Meal> => {
  const response = await apiClient.get<Meal>(`/meals/${mealId}`);
  return response.data;
};

/**
 * 食事記録を更新
 */
export const updateMeal = async (
  mealId: string,
  data: UpdateMealRequest
): Promise<Meal> => {
  const response = await apiClient.put<Meal>(`/meals/${mealId}`, data);
  return response.data;
};

/**
 * 食事記録を削除
 */
export const deleteMeal = async (mealId: string): Promise<void> => {
  await apiClient.delete(`/meals/${mealId}`);
};
