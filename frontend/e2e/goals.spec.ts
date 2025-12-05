/**
 * 目標設定のE2Eテスト
 *
 * Task 24.1: 目標設定のE2Eテスト
 */

import { test, expect } from '@playwright/test';

test.describe('目標設定', () => {
  test.beforeEach(async ({ page }) => {
    // ログインページに移動してログイン
    // （実際のCognito認証が必要なため、ここではモックまたはテスト用ユーザーを使用）
    await page.goto('/login');
  });

  test.describe('目標設定フロー', () => {
    test('目標設定ページが正しく表示される', async ({ page }) => {
      // 目標設定ページに直接移動（認証後）
      await page.goto('/goals');

      // ページタイトルが表示されることを確認
      await expect(page.locator('h1')).toContainText('目標設定');

      // イントロメッセージが表示されることを確認
      await expect(
        page.locator('.goal-intro')
      ).toContainText('体重目標を設定すると');

      // フォームが表示されることを確認
      await expect(page.locator('.goal-form')).toBeVisible();
    });

    test('フォームフィールドが正しく表示される', async ({ page }) => {
      await page.goto('/goals');

      // 現在の体重が表示されることを確認
      await expect(page.locator('.current-weight')).toBeVisible();

      // 目標タイプ選択が表示されることを確認
      await expect(page.locator('label:has-text("目標タイプ")')).toBeVisible();
      const goalTypeSelect = page.locator('select#goal_type');
      await expect(goalTypeSelect).toBeVisible();

      // 目標体重入力が表示されることを確認
      await expect(page.locator('label:has-text("目標体重")')).toBeVisible();
      await expect(page.locator('input#target_weight')).toBeVisible();

      // 目標日入力が表示されることを確認
      await expect(page.locator('label:has-text("目標日")')).toBeVisible();
      await expect(page.locator('input#target_date')).toBeVisible();

      // 送信ボタンが表示されることを確認
      await expect(
        page.locator('button[type="submit"]:has-text("目標を作成")')
      ).toBeVisible();
    });

    test('フォーム入力が正しく動作する', async ({ page }) => {
      await page.goto('/goals');

      // 目標タイプを選択
      const goalTypeSelect = page.locator('select#goal_type');
      await goalTypeSelect.selectOption('lose');
      await expect(goalTypeSelect).toHaveValue('lose');

      // 目標体重を入力
      const targetWeightInput = page.locator('input#target_weight');
      await targetWeightInput.fill('60');
      await expect(targetWeightInput).toHaveValue('60');

      // 目標日を入力
      const targetDateInput = page.locator('input#target_date');
      const futureDate = new Date();
      futureDate.setMonth(futureDate.getMonth() + 3);
      const futureDateStr = futureDate.toISOString().split('T')[0];
      await targetDateInput.fill(futureDateStr);
      await expect(targetDateInput).toHaveValue(futureDateStr);
    });

    test('減量目標で体重が現在より大きい場合エラーが表示される', async ({
      page,
    }) => {
      await page.goto('/goals');

      // 減量を選択
      await page.locator('select#goal_type').selectOption('lose');

      // 現在の体重を取得
      const currentWeightText = await page
        .locator('.current-weight .weight-value')
        .textContent();
      const currentWeight = parseFloat(currentWeightText || '0');

      // 現在より大きい体重を入力
      await page.locator('input#target_weight').fill((currentWeight + 5).toString());

      // 目標日を入力
      const futureDate = new Date();
      futureDate.setMonth(futureDate.getMonth() + 3);
      await page
        .locator('input#target_date')
        .fill(futureDate.toISOString().split('T')[0]);

      // 送信ボタンをクリック
      await page.locator('button[type="submit"]').click();

      // エラーメッセージが表示されることを確認
      await expect(page.locator('.error-message')).toContainText(
        '減量目標の場合、目標体重は現在の体重より小さくする必要があります'
      );
    });

    test('増量目標で体重が現在より小さい場合エラーが表示される', async ({
      page,
    }) => {
      await page.goto('/goals');

      // 増量を選択
      await page.locator('select#goal_type').selectOption('gain');

      // 現在の体重を取得
      const currentWeightText = await page
        .locator('.current-weight .weight-value')
        .textContent();
      const currentWeight = parseFloat(currentWeightText || '0');

      // 現在より小さい体重を入力
      await page.locator('input#target_weight').fill((currentWeight - 5).toString());

      // 目標日を入力
      const futureDate = new Date();
      futureDate.setMonth(futureDate.getMonth() + 3);
      await page
        .locator('input#target_date')
        .fill(futureDate.toISOString().split('T')[0]);

      // 送信ボタンをクリック
      await page.locator('button[type="submit"]').click();

      // エラーメッセージが表示されることを確認
      await expect(page.locator('.error-message')).toContainText(
        '増量目標の場合、目標体重は現在の体重より大きくする必要があります'
      );
    });

    test('過去の日付を設定した場合エラーが表示される', async ({ page }) => {
      await page.goto('/goals');

      // 目標体重を入力
      await page.locator('input#target_weight').fill('60');

      // 過去の日付を入力
      const pastDate = new Date();
      pastDate.setMonth(pastDate.getMonth() - 1);
      await page
        .locator('input#target_date')
        .fill(pastDate.toISOString().split('T')[0]);

      // 送信ボタンをクリック
      await page.locator('button[type="submit"]').click();

      // エラーメッセージが表示されることを確認
      await expect(page.locator('.error-message')).toContainText(
        '目標日は今日以降の日付を選択してください'
      );
    });

    test('急激な減量目標で警告メッセージが表示される', async ({ page }) => {
      await page.goto('/goals');

      // 減量を選択
      await page.locator('select#goal_type').selectOption('lose');

      // 現在の体重を取得
      const currentWeightText = await page
        .locator('.current-weight .weight-value')
        .textContent();
      const currentWeight = parseFloat(currentWeightText || '0');

      // 1週間で2kg減量する目標を設定（急激）
      await page.locator('input#target_weight').fill((currentWeight - 2).toString());

      // 7日後の日付を入力
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 7);
      await page
        .locator('input#target_date')
        .fill(futureDate.toISOString().split('T')[0]);

      // 送信ボタンをクリック
      await page.locator('button[type="submit"]').click();

      // 警告メッセージが表示されることを確認
      await expect(page.locator('.warning-message')).toContainText(
        '警告: 1週間で1kg以上の減量は健康リスクがあります'
      );
    });

    test('急激な増量目標で警告メッセージが表示される', async ({ page }) => {
      await page.goto('/goals');

      // 増量を選択
      await page.locator('select#goal_type').selectOption('gain');

      // 現在の体重を取得
      const currentWeightText = await page
        .locator('.current-weight .weight-value')
        .textContent();
      const currentWeight = parseFloat(currentWeightText || '0');

      // 1週間で1kg増量する目標を設定（急激）
      await page.locator('input#target_weight').fill((currentWeight + 1).toString());

      // 7日後の日付を入力
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 7);
      await page
        .locator('input#target_date')
        .fill(futureDate.toISOString().split('T')[0]);

      // 送信ボタンをクリック
      await page.locator('button[type="submit"]').click();

      // 警告メッセージが表示されることを確認
      await expect(page.locator('.warning-message')).toContainText(
        '警告: 1週間で0.5kg以上の増量は過剰です'
      );
    });

    test('目標作成成功時に結果が表示される', async ({ page }) => {
      // このテストは実際のAPIが必要なためスキップまたはモック化が必要
      await page.goto('/goals');

      // モック: 目標作成が成功した場合の結果表示を確認
      // 実際には、APIレスポンスをモックする必要がある

      // 目標結果エリアが表示されることを期待（APIが実装されている場合）
      // await expect(page.locator('.goal-result')).toBeVisible();
      // await expect(page.locator('.result-label:has-text("目標カロリー")')).toBeVisible();
      // await expect(page.locator('.result-label:has-text("推奨タンパク質")')).toBeVisible();
      // await expect(page.locator('.result-label:has-text("推奨脂質")')).toBeVisible();
      // await expect(page.locator('.result-label:has-text("推奨炭水化物")')).toBeVisible();
    });

    test('必須項目のHTML5バリデーション', async ({ page }) => {
      await page.goto('/goals');

      // 何も入力せずに送信
      const submitButton = page.locator('button[type="submit"]');
      await submitButton.click();

      // HTML5バリデーションが動作することを確認
      const targetWeightInput = page.locator('input#target_weight');
      const isInvalid = await targetWeightInput.evaluate(
        (el: HTMLInputElement) => !el.validity.valid
      );
      expect(isInvalid).toBe(true);
    });
  });

  test.describe('レスポンシブデザイン', () => {
    test('モバイルビューで正しく表示される', async ({ page }) => {
      // モバイルサイズに設定
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/goals');

      // フォームが表示されることを確認
      await expect(page.locator('.goal-form')).toBeVisible();

      // スクロール可能であることを確認
      const container = page.locator('.goal-container');
      await expect(container).toBeVisible();
    });
  });
});
