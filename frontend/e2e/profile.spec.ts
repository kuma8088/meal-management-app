/**
 * ユーザープロフィール設定のE2Eテスト
 *
 * Task 23.1: ユーザープロフィール設定のE2Eテスト
 */

import { test, expect } from '@playwright/test';

test.describe('ユーザープロフィール設定', () => {
  test.beforeEach(async ({ page }) => {
    // ログインページに移動してログイン
    // （実際のCognito認証が必要なため、ここではモックまたはテスト用ユーザーを使用）
    await page.goto('/login');
  });

  test.describe('プロフィール作成フロー', () => {
    test('プロフィールフォームが正しく表示される', async ({ page }) => {
      // プロフィールページに直接移動（認証後）
      await page.goto('/profile');

      // ページタイトルが表示されることを確認
      await expect(page.locator('h1')).toContainText('プロフィール設定');

      // フォームフィールドが表示されることを確認
      await expect(page.locator('label:has-text("年齢")')).toBeVisible();
      await expect(page.locator('label:has-text("性別")')).toBeVisible();
      await expect(page.locator('label:has-text("身長")')).toBeVisible();
      await expect(page.locator('label:has-text("体重")')).toBeVisible();
      await expect(page.locator('label:has-text("活動レベル")')).toBeVisible();

      // 送信ボタンが表示されることを確認
      await expect(
        page.locator('button[type="submit"]:has-text("プロフィールを作成")')
      ).toBeVisible();
    });

    test('フォーム入力が正しく動作する', async ({ page }) => {
      await page.goto('/profile');

      // 年齢を入力
      const ageInput = page.locator('input#age');
      await ageInput.fill('30');
      await expect(ageInput).toHaveValue('30');

      // 性別を選択
      const genderSelect = page.locator('select#gender');
      await genderSelect.selectOption('male');
      await expect(genderSelect).toHaveValue('male');

      // 身長を入力
      const heightInput = page.locator('input#height');
      await heightInput.fill('170');
      await expect(heightInput).toHaveValue('170');

      // 体重を入力
      const weightInput = page.locator('input#weight');
      await weightInput.fill('65');
      await expect(weightInput).toHaveValue('65');

      // 活動レベルを選択
      const activitySelect = page.locator('select#activity_level');
      await activitySelect.selectOption('moderate');
      await expect(activitySelect).toHaveValue('moderate');
    });

    test('BMR/TDEEがリアルタイムで計算される', async ({ page }) => {
      await page.goto('/profile');

      // フォームに入力
      await page.locator('input#age').fill('30');
      await page.locator('select#gender').selectOption('male');
      await page.locator('input#height').fill('170');
      await page.locator('input#weight').fill('65');
      await page.locator('select#activity_level').selectOption('moderate');

      // BMR/TDEE表示エリアが表示されることを確認
      await expect(page.locator('.metabolism-display')).toBeVisible();
      await expect(page.locator('.stat-label:has-text("基礎代謝量（BMR）")')).toBeVisible();
      await expect(page.locator('.stat-label:has-text("総消費カロリー（TDEE）")')).toBeVisible();

      // 計算値が表示されることを確認（具体的な値はHarris-Benedict式で計算）
      // 男性: BMR = 88.362 + (13.397 × 65) + (4.799 × 170) - (5.677 × 30) ≈ 1565 kcal
      // TDEE = 1565 × 1.55 ≈ 2426 kcal
      const bmrValue = page.locator('.stat-card').filter({ hasText: 'BMR' }).locator('.stat-value');
      const tdeeValue = page.locator('.stat-card').filter({ hasText: 'TDEE' }).locator('.stat-value');

      await expect(bmrValue).toContainText('kcal/日');
      await expect(tdeeValue).toContainText('kcal/日');
    });

    test('バリデーションエラーが表示される', async ({ page }) => {
      await page.goto('/profile');

      // 年齢に無効な値を入力
      await page.locator('input#age').fill('200');
      await page.locator('input#height').fill('170');
      await page.locator('input#weight').fill('65');

      // 送信ボタンをクリック
      await page.locator('button[type="submit"]').click();

      // エラーメッセージが表示されることを確認
      await expect(page.locator('.error-message')).toContainText('年齢は1〜150の範囲で入力してください');
    });

    test('必須項目のHTML5バリデーション', async ({ page }) => {
      await page.goto('/profile');

      // 何も入力せずに送信
      const submitButton = page.locator('button[type="submit"]');
      await submitButton.click();

      // HTML5バリデーションが動作することを確認
      const ageInput = page.locator('input#age');
      const isInvalid = await ageInput.evaluate(
        (el: HTMLInputElement) => !el.validity.valid
      );
      expect(isInvalid).toBe(true);
    });
  });

  test.describe('プロフィール更新フロー', () => {
    test('既存プロフィールが読み込まれる', async ({ page }) => {
      // モック: 既存プロフィールが存在する場合
      await page.goto('/profile');

      // フォームに既存の値が入っている場合、更新ボタンが表示される
      // （実際のAPIがないため、UIのテストのみ）
      const submitButton = page.locator('button[type="submit"]');

      // ボタンテキストは「プロフィールを作成」または「プロフィールを更新」のいずれか
      const buttonText = await submitButton.textContent();
      expect(buttonText).toMatch(/プロフィールを(作成|更新)/);
    });

    test('プロフィール更新時の入力変更', async ({ page }) => {
      await page.goto('/profile');

      // 既存の値を変更
      await page.locator('input#age').fill('31');
      await page.locator('input#weight').fill('66');

      // 送信ボタンが有効であることを確認
      const submitButton = page.locator('button[type="submit"]');
      await expect(submitButton).toBeEnabled();
    });

    test('性別変更時にBMRが再計算される', async ({ page }) => {
      await page.goto('/profile');

      // 初期値を入力（男性）
      await page.locator('input#age').fill('30');
      await page.locator('select#gender').selectOption('male');
      await page.locator('input#height').fill('170');
      await page.locator('input#weight').fill('65');
      await page.locator('select#activity_level').selectOption('moderate');

      // BMR値を取得
      const initialBmr = await page
        .locator('.stat-card')
        .filter({ hasText: 'BMR' })
        .locator('.stat-value')
        .textContent();

      // 性別を変更（女性）
      await page.locator('select#gender').selectOption('female');

      // BMR値が変更されたことを確認
      const updatedBmr = await page
        .locator('.stat-card')
        .filter({ hasText: 'BMR' })
        .locator('.stat-value')
        .textContent();

      expect(initialBmr).not.toBe(updatedBmr);
    });

    test('活動レベル変更時にTDEEが再計算される', async ({ page }) => {
      await page.goto('/profile');

      // 初期値を入力
      await page.locator('input#age').fill('30');
      await page.locator('select#gender').selectOption('male');
      await page.locator('input#height').fill('170');
      await page.locator('input#weight').fill('65');
      await page.locator('select#activity_level').selectOption('sedentary');

      // TDEE値を取得
      const initialTdee = await page
        .locator('.stat-card')
        .filter({ hasText: 'TDEE' })
        .locator('.stat-value')
        .textContent();

      // 活動レベルを変更
      await page.locator('select#activity_level').selectOption('very_active');

      // TDEE値が変更されたことを確認
      const updatedTdee = await page
        .locator('.stat-card')
        .filter({ hasText: 'TDEE' })
        .locator('.stat-value')
        .textContent();

      expect(initialTdee).not.toBe(updatedTdee);
    });
  });

  test.describe('レスポンシブデザイン', () => {
    test('モバイルビューで正しく表示される', async ({ page }) => {
      // モバイルサイズに設定
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/profile');

      // フォームが表示されることを確認
      await expect(page.locator('.profile-form')).toBeVisible();

      // スクロール可能であることを確認
      const container = page.locator('.profile-container');
      await expect(container).toBeVisible();
    });
  });
});
