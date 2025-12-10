/**
 * 食品検索API
 */

import { apiClient } from './client';
import type { Food, SearchFoodParams } from '../types/api';

/**
 * 食品検索レスポンス
 */
interface FoodSearchResponse {
  foods: Food[];
  count: number;
  ai_search_available?: boolean;
  message?: string;
}

/**
 * 食品を検索
 */
export const searchFoods = async (params: SearchFoodParams): Promise<Food[]> => {
  const response = await apiClient.get<FoodSearchResponse>('/foods/search', { params });
  // レスポンスデータの安全な抽出（undefined/null対策）
  return response.data?.foods ?? [];
};

/**
 * 食品名で検索
 */
export const searchFoodsByName = async (name: string): Promise<Food[]> => {
  return searchFoods({ query: name });
};

/**
 * 特定の食品を取得
 */
export const getFood = async (foodId: string): Promise<Food> => {
  const response = await apiClient.get<Food>(`/foods/${foodId}`);
  return response.data;
};
