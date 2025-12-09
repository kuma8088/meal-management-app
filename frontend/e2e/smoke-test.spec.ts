/**
 * スモークテスト - Device Farm 用最小限テスト
 *
 * 5個の必須テストのみ（10分以内完了目標）
 * - ホームページ表示
 * - 食事登録ページアクセス
 * - 食事一覧ページ表示
 * - 目標設定ページアクセス
 * - プロフィールページ表示
 */

import { test, expect } from '@playwright/test';

test.describe('【Smoke Test】基本動作確認', () => {
  test.describe.configure({ timeout: 60000 }); // 各テスト最大60秒

  test('1. ホームページが正しく表示される', async ({ page }) => {
    await page.goto('/');

    // ホームページの基本要素を確認
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('nav')).toBeVisible();
  });

  test('2. 食事登録ページにアクセスできる', async ({ page }) => {
    await page.goto('/meals/new');

    // フォーム要素が表示されている
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('form')).toBeVisible();
  });

  test('3. 食事一覧ページが表示される', async ({ page }) => {
    await page.goto('/meals');

    // ページが正しく表示される
    await expect(page.locator('h1')).toBeVisible();
  });

  test('4. 目標設定ページにアクセスできる', async ({ page }) => {
    await page.goto('/goals');

    // ページが正しく表示される
    await expect(page.locator('h1')).toBeVisible();
  });

  test('5. プロフィールページが表示される', async ({ page }) => {
    await page.goto('/profile');

    // ページが正しく表示される
    await expect(page.locator('h1')).toBeVisible();
  });
});
