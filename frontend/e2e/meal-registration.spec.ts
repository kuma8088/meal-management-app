/**
 * 食事登録のE2Eテスト
 *
 * Task 26.1: 食事登録のE2Eテスト
 */

import { test, expect } from '@playwright/test';
import { mockFoodSearch, mockCreateMeal, sampleFoods, createSampleMeal } from './helpers/api-mocks';

test.describe('食事登録', () => {
  test.beforeEach(async ({ page }) => {
    // APIモックを先に設定
    await mockFoodSearch(page, sampleFoods);

    // 食事登録ページに移動
    await page.goto('/meals/new');
  });

  test.describe('食事登録ページ', () => {
    test('食事登録ページが正しく表示される', async ({ page }) => {
      // ページタイトルが表示されることを確認
      await expect(page.locator('h1')).toContainText('食事登録');

      // イントロメッセージが表示されることを確認
      await expect(page.locator('.page-intro')).toContainText(
        '食品を検索して追加し、食事を記録しましょう'
      );

      // フォームが表示されることを確認
      await expect(page.locator('.meal-registration-form')).toBeVisible();
    });

    test('フォーム要素が正しく表示される', async ({ page }) => {
      // 食事タイプ選択が表示される
      await expect(page.locator('label:has-text("食事タイプ")')).toBeVisible();
      await expect(page.locator('#meal-type')).toBeVisible();

      // 日時入力が表示される
      await expect(page.locator('label:has-text("日時")')).toBeVisible();
      await expect(page.locator('#timestamp')).toBeVisible();

      // 食品検索が表示される
      await expect(page.locator('label:has-text("食品検索")')).toBeVisible();
      await expect(page.locator('#food-search')).toBeVisible();
      await expect(page.locator('.search-button')).toBeVisible();

      // 登録ボタンが表示される（初期状態では無効）
      const submitButton = page.locator('.submit-button');
      await expect(submitButton).toBeVisible();
      await expect(submitButton).toBeDisabled();
    });
  });

  test.describe('食事タイプ選択', () => {
    test('食事タイプを選択できる', async ({ page }) => {
      const mealTypeSelect = page.locator('#meal-type');

      // デフォルトは朝食
      await expect(mealTypeSelect).toHaveValue('breakfast');

      // 昼食を選択
      await mealTypeSelect.selectOption('lunch');
      await expect(mealTypeSelect).toHaveValue('lunch');

      // 夕食を選択
      await mealTypeSelect.selectOption('dinner');
      await expect(mealTypeSelect).toHaveValue('dinner');

      // 間食を選択
      await mealTypeSelect.selectOption('snack');
      await expect(mealTypeSelect).toHaveValue('snack');
    });

    test('食事タイプの選択肢が正しく表示される', async ({ page }) => {
      const options = page.locator('#meal-type option');

      await expect(options).toHaveCount(4);
      await expect(options.nth(0)).toHaveText('朝食');
      await expect(options.nth(1)).toHaveText('昼食');
      await expect(options.nth(2)).toHaveText('夕食');
      await expect(options.nth(3)).toHaveText('間食');
    });
  });

  test.describe('日時入力', () => {
    test('日時を変更できる', async ({ page }) => {
      const timestampInput = page.locator('#timestamp');

      // 初期値が設定されている（現在時刻）
      const initialValue = await timestampInput.inputValue();
      expect(initialValue).toBeTruthy();

      // 日時を変更
      const newTimestamp = '2025-12-06T12:00';
      await timestampInput.fill(newTimestamp);
      await expect(timestampInput).toHaveValue(newTimestamp);
    });
  });

  test.describe('食品検索', () => {
    test('食品検索フィールドに入力できる', async ({ page }) => {
      const searchInput = page.locator('#food-search');

      await searchInput.fill('りんご');
      await expect(searchInput).toHaveValue('りんご');
    });

    test('空の検索でエラーメッセージが表示される', async ({ page }) => {
      const searchButton = page.locator('.search-button');

      // 空のまま検索
      await searchButton.click();

      // エラーメッセージが表示される
      await expect(page.locator('.error-message')).toContainText(
        '食品名を入力してください'
      );
    });

    test('食品検索結果が表示される', async ({ page }) => {
      const searchInput = page.locator('#food-search');
      const searchButton = page.locator('.search-button');

      // 食品を検索
      await searchInput.fill('りんご');

      // レスポンスを待つ
      const responsePromise = page.waitForResponse('**/foods/search*');
      await searchButton.click();
      await responsePromise;

      // 検索結果が表示される
      await expect(page.locator('.search-results')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('.search-result-item').first()).toBeVisible();

      // りんごが表示される
      await expect(page.locator('.food-name').first()).toContainText('りんご');
    });

    test('検索結果から食品を追加できる', async ({ page }) => {
      const searchInput = page.locator('#food-search');
      const searchButton = page.locator('.search-button');

      // 食品を検索
      await searchInput.fill('りんご');

      const responsePromise = page.waitForResponse('**/foods/search*');
      await searchButton.click();
      await responsePromise;

      // 検索結果が表示されるまで待つ
      await expect(page.locator('.add-button').first()).toBeVisible({ timeout: 10000 });

      // 最初の結果を追加
      await page.locator('.add-button').first().click();

      // 食品リストに追加される
      await expect(page.locator('.foods-list')).toBeVisible();
      await expect(page.locator('.food-item').first()).toBeVisible();

      // 食品名が表示される
      await expect(page.locator('.food-item-name').first()).toContainText('りんご');
    });
  });

  test.describe('食品リスト管理', () => {
    test('追加された食品が表示される', async ({ page }) => {
      // 食品を検索して追加
      await page.locator('#food-search').fill('りんご');

      const responsePromise = page.waitForResponse('**/foods/search*');
      await page.locator('.search-button').click();
      await responsePromise;

      await expect(page.locator('.add-button').first()).toBeVisible({ timeout: 10000 });
      await page.locator('.add-button').first().click();

      // 食品リストが表示される
      const foodItem = page.locator('.food-item').first();
      await expect(foodItem).toBeVisible();

      // 食品名が表示される
      await expect(foodItem.locator('.food-item-name')).toContainText('りんご');

      // 量入力フィールドが表示される
      await expect(foodItem.locator('input[type="number"]')).toBeVisible();

      // 削除ボタンが表示される
      await expect(foodItem.locator('.remove-button')).toBeVisible();
    });

    test('食品の量を変更できる', async ({ page }) => {
      // 食品を検索して追加
      await page.locator('#food-search').fill('りんご');

      const responsePromise = page.waitForResponse('**/foods/search*');
      await page.locator('.search-button').click();
      await responsePromise;

      await expect(page.locator('.add-button').first()).toBeVisible({ timeout: 10000 });
      await page.locator('.add-button').first().click();

      const amountInput = page.locator('.food-item').first().locator('input[type="number"]');

      // 初期値は100
      await expect(amountInput).toHaveValue('100');

      // 量を変更
      await amountInput.fill('200');
      await expect(amountInput).toHaveValue('200');
    });

    test('食品を削除できる', async ({ page }) => {
      // 食品を検索して追加
      await page.locator('#food-search').fill('りんご');

      const responsePromise = page.waitForResponse('**/foods/search*');
      await page.locator('.search-button').click();
      await responsePromise;

      await expect(page.locator('.add-button').first()).toBeVisible({ timeout: 10000 });
      await page.locator('.add-button').first().click();

      const foodItem = page.locator('.food-item').first();
      await expect(foodItem).toBeVisible();

      // 削除ボタンをクリック
      await foodItem.locator('.remove-button').click();

      // 食品リストから削除される
      await expect(page.locator('.foods-list')).not.toBeVisible();
    });
  });

  test.describe('栄養情報表示', () => {
    test('栄養情報サマリーが表示される', async ({ page }) => {
      // 食品を検索して追加
      await page.locator('#food-search').fill('りんご');

      const responsePromise = page.waitForResponse('**/foods/search*');
      await page.locator('.search-button').click();
      await responsePromise;

      await expect(page.locator('.add-button').first()).toBeVisible({ timeout: 10000 });
      await page.locator('.add-button').first().click();

      // 栄養情報サマリーが表示される
      await expect(page.locator('.nutrition-summary')).toBeVisible();

      // 各栄養素が表示される
      await expect(page.locator('.nutrition-label:has-text("カロリー")')).toBeVisible();
      await expect(page.locator('.nutrition-label:has-text("たんぱく質")')).toBeVisible();
      await expect(page.locator('.nutrition-label:has-text("脂質")')).toBeVisible();
      await expect(page.locator('.nutrition-label:has-text("炭水化物")')).toBeVisible();
    });

    test('複数食品の栄養情報が正しく合計される', async ({ page }) => {
      // りんごを追加
      await page.locator('#food-search').fill('りんご');

      let responsePromise = page.waitForResponse('**/foods/search*');
      await page.locator('.search-button').click();
      await responsePromise;

      await expect(page.locator('.add-button').first()).toBeVisible({ timeout: 10000 });
      await page.locator('.add-button').first().click();

      // バナナを検索して追加
      await page.locator('#food-search').fill('バナナ');

      responsePromise = page.waitForResponse('**/foods/search*');
      await page.locator('.search-button').click();
      await responsePromise;

      await expect(page.locator('.search-result-item').filter({ hasText: 'バナナ' }).locator('.add-button')).toBeVisible({ timeout: 10000 });
      await page.locator('.search-result-item').filter({ hasText: 'バナナ' }).locator('.add-button').click();

      // 栄養情報の合計値が表示される（りんご54 + バナナ86 = 140 kcal）
      const totalCalories = page.locator('.nutrition-value').first();
      const caloriesText = await totalCalories.textContent();

      // カロリーが数値として表示されている
      expect(caloriesText).toMatch(/140\.0 kcal/);
    });
  });

  test.describe('食事登録', () => {
    test('食品が追加されていない状態では登録ボタンが無効', async ({ page }) => {
      const submitButton = page.locator('.submit-button');

      // 登録ボタンが無効
      await expect(submitButton).toBeDisabled();
    });

    test('食事を登録できる', async ({ page }) => {
      // 食事作成APIモックを設定
      await mockCreateMeal(page, createSampleMeal());

      // 食事タイプを選択
      await page.locator('#meal-type').selectOption('lunch');

      // 食品を検索して追加
      await page.locator('#food-search').fill('りんご');

      const responsePromise = page.waitForResponse('**/foods/search*');
      await page.locator('.search-button').click();
      await responsePromise;

      await expect(page.locator('.add-button').first()).toBeVisible({ timeout: 10000 });
      await page.locator('.add-button').first().click();

      // 登録ボタンをクリック
      const submitButton = page.locator('.submit-button');
      await expect(submitButton).toBeEnabled();

      const createMealPromise = page.waitForResponse('**/meals');
      await submitButton.click();
      await createMealPromise;

      // 成功メッセージが表示される
      await expect(page.locator('.success-message')).toContainText(
        '食事を登録しました',
        { timeout: 10000 }
      );
    });
  });

  test.describe('レスポンシブデザイン', () => {
    test('モバイルビューで正しく表示される', async ({ page }) => {
      // モバイルサイズに変更
      await page.setViewportSize({ width: 375, height: 667 });

      // ページが表示される
      await expect(page.locator('h1')).toContainText('食事登録');

      // フォームが表示される
      await expect(page.locator('.meal-registration-form')).toBeVisible();

      // スクロール可能であることを確認
      const container = page.locator('.meal-registration-container');
      await expect(container).toBeVisible();
    });
  });
});
