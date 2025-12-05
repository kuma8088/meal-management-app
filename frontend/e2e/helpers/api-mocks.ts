/**
 * E2EテストのためのAPIモックヘルパー
 */

import { Page } from '@playwright/test';
import type { Food, Meal } from '../../src/types/api';

/**
 * 食品検索APIをモック
 */
export async function mockFoodSearch(page: Page, foods: Food[]) {
  await page.route('**/foods/search*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(foods),
    });
  });
}

/**
 * 食事作成APIをモック
 */
export async function mockCreateMeal(page: Page, meal: Meal) {
  await page.route('**/meals', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(meal),
      });
    } else {
      await route.continue();
    }
  });
}

/**
 * テスト用のサンプル食品データ
 */
export const sampleFoods: Food[] = [
  {
    food_id: 'food_001',
    name: 'りんご',
    calories_per_100g: 54,
    protein_per_100g: 0.2,
    fat_per_100g: 0.1,
    carbs_per_100g: 14.1,
    source: 'STANDARD_TABLES',
  },
  {
    food_id: 'food_002',
    name: 'バナナ',
    calories_per_100g: 86,
    protein_per_100g: 1.1,
    fat_per_100g: 0.2,
    carbs_per_100g: 22.5,
    source: 'STANDARD_TABLES',
  },
  {
    food_id: 'food_003',
    name: '白米（炊飯済み）',
    calories_per_100g: 168,
    protein_per_100g: 2.5,
    fat_per_100g: 0.3,
    carbs_per_100g: 37.1,
    source: 'STANDARD_TABLES',
  },
];

/**
 * テスト用のサンプル食事データ
 */
export function createSampleMeal(overrides?: Partial<Meal>): Meal {
  return {
    meal_id: 'meal_001',
    user_id: 'user_001',
    meal_type: 'lunch',
    timestamp: new Date().toISOString(),
    foods: [
      {
        food_id: 'food_001',
        name: 'りんご',
        amount: 100,
        unit: 'g',
        calories: 54,
        protein: 0.2,
        fat: 0.1,
        carbs: 14.1,
      },
    ],
    total_calories: 54,
    total_protein: 0.2,
    total_fat: 0.1,
    total_carbs: 14.1,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}
