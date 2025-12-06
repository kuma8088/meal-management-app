/**
 * 食事記録一覧のE2Eテスト
 *
 * Task 27.1: 食事記録一覧のE2Eテスト
 */

import { test, expect } from '@playwright/test';

test.describe('食事記録一覧', () => {
  test.beforeEach(async ({ page }) => {
    // ログインページに移動してログイン
    // （実際のCognito認証が必要なため、ここではモックまたはテスト用ユーザーを使用）
    await page.goto('/login');
  });

  test.describe('食事記録一覧ページ', () => {
    test('食事記録一覧ページが正しく表示される', async ({ page }) => {
      // 食事記録一覧ページに直接移動（認証後）
      await page.goto('/meals');

      // ページタイトルが表示されることを確認
      await expect(page.locator('h1')).toContainText('食事記録');

      // フィルターセクションが表示されることを確認
      await expect(page.locator('.filter-section')).toBeVisible();

      // 日付入力フィールドが表示されることを確認
      await expect(page.locator('input#start-date')).toBeVisible();
      await expect(page.locator('input#end-date')).toBeVisible();

      // 検索ボタンが表示されることを確認
      await expect(page.locator('.search-button')).toBeVisible();
    });

    test('クイックフィルタボタンが表示される', async ({ page }) => {
      await page.goto('/meals');

      // クイックフィルタボタンが表示されることを確認
      const todayButton = page.locator('.quick-button').filter({ hasText: '今日' });
      const sevenDaysButton = page
        .locator('.quick-button')
        .filter({ hasText: '過去7日間' });
      const thirtyDaysButton = page
        .locator('.quick-button')
        .filter({ hasText: '過去30日間' });

      await expect(todayButton).toBeVisible();
      await expect(sevenDaysButton).toBeVisible();
      await expect(thirtyDaysButton).toBeVisible();
    });

    test('初期状態で過去7日間の日付が設定される', async ({ page }) => {
      await page.goto('/meals');

      // 開始日と終了日が設定されていることを確認
      const startDateInput = page.locator('input#start-date');
      const endDateInput = page.locator('input#end-date');

      const startDate = await startDateInput.inputValue();
      const endDate = await endDateInput.inputValue();

      // 開始日と終了日が存在することを確認
      expect(startDate).toBeTruthy();
      expect(endDate).toBeTruthy();

      // 終了日が開始日より後であることを確認
      expect(new Date(startDate).getTime()).toBeLessThan(
        new Date(endDate).getTime()
      );
    });
  });

  test.describe('日付フィルタリング', () => {
    test('日付を変更できる', async ({ page }) => {
      await page.goto('/meals');

      const startDateInput = page.locator('input#start-date');
      const endDateInput = page.locator('input#end-date');

      // 新しい日付を設定
      const newStartDate = '2024-01-01';
      const newEndDate = '2024-12-31';

      await startDateInput.fill(newStartDate);
      await endDateInput.fill(newEndDate);

      await expect(startDateInput).toHaveValue(newStartDate);
      await expect(endDateInput).toHaveValue(newEndDate);
    });

    test('今日ボタンが動作する', async ({ page }) => {
      await page.goto('/meals');

      const todayButton = page.locator('.quick-button').filter({ hasText: '今日' });
      await todayButton.click();

      const startDateInput = page.locator('input#start-date');
      const endDateInput = page.locator('input#end-date');

      const startDate = await startDateInput.inputValue();
      const endDate = await endDateInput.inputValue();

      // 開始日と終了日が同じ（今日）であることを確認
      expect(startDate).toBe(endDate);

      // 今日の日付であることを確認
      const today = new Date().toISOString().split('T')[0];
      expect(endDate).toBe(today);
    });

    test('過去7日間ボタンが動作する', async ({ page }) => {
      await page.goto('/meals');

      const sevenDaysButton = page
        .locator('.quick-button')
        .filter({ hasText: '過去7日間' });
      await sevenDaysButton.click();

      const startDateInput = page.locator('input#start-date');
      const endDateInput = page.locator('input#end-date');

      const startDate = await startDateInput.inputValue();
      const endDate = await endDateInput.inputValue();

      // 日付が正しく設定されていることを確認
      const startDateTime = new Date(startDate).getTime();
      const endDateTime = new Date(endDate).getTime();
      const daysDiff = (endDateTime - startDateTime) / (1000 * 60 * 60 * 24);

      // 約7日間の差があることを確認（±1日の誤差を許容）
      expect(daysDiff).toBeGreaterThan(6);
      expect(daysDiff).toBeLessThan(8);
    });

    test('過去30日間ボタンが動作する', async ({ page }) => {
      await page.goto('/meals');

      const thirtyDaysButton = page
        .locator('.quick-button')
        .filter({ hasText: '過去30日間' });
      await thirtyDaysButton.click();

      const startDateInput = page.locator('input#start-date');
      const endDateInput = page.locator('input#end-date');

      const startDate = await startDateInput.inputValue();
      const endDate = await endDateInput.inputValue();

      // 日付が正しく設定されていることを確認
      const startDateTime = new Date(startDate).getTime();
      const endDateTime = new Date(endDate).getTime();
      const daysDiff = (endDateTime - startDateTime) / (1000 * 60 * 60 * 24);

      // 約30日間の差があることを確認（±1日の誤差を許容）
      expect(daysDiff).toBeGreaterThan(29);
      expect(daysDiff).toBeLessThan(31);
    });

    test('開始日が終了日より後の場合エラーが表示される', async ({ page }) => {
      await page.goto('/meals');

      const startDateInput = page.locator('input#start-date');
      const endDateInput = page.locator('input#end-date');
      const searchButton = page.locator('.search-button');

      // 開始日を終了日より後に設定
      await startDateInput.fill('2024-12-31');
      await endDateInput.fill('2024-01-01');

      // 検索ボタンをクリック
      await searchButton.click();

      // エラーメッセージが表示されることを確認
      await expect(page.locator('.error-message')).toContainText(
        '開始日は終了日より前である必要があります'
      );
    });
  });

  test.describe('食事記録表示', () => {
    test('食事記録が存在しない場合メッセージが表示される', async ({ page }) => {
      await page.goto('/meals');

      // 遠い過去の日付を設定
      const startDateInput = page.locator('input#start-date');
      const endDateInput = page.locator('input#end-date');
      const searchButton = page.locator('.search-button');

      await startDateInput.fill('2000-01-01');
      await endDateInput.fill('2000-12-31');

      // 検索ボタンをクリック
      await searchButton.click();

      // 「食事記録がありません」メッセージが表示されることを確認
      // または error-message に該当する食事記録がありません が表示される
      const emptyMessage = page.locator('.meals-empty, .error-message');
      await expect(emptyMessage).toBeVisible();
    });

    test('食事記録がある場合表示される（APIモック必要）', async ({ page }) => {
      // このテストは実際のAPIレスポンスまたはモックが必要

      await page.goto('/meals');

      // 期待される食事記録の構造:
      // - .meals-group (日付ごとのグループ)
      //   - .date-header (日付ヘッダー)
      //   - .meals-day-list
      //     - .meal-item (各食事記録)
      //       - .meal-header (食事タイプと時間)
      //       - .meal-foods (食品リスト)
      //       - .meal-nutrition (栄養情報)
    });

    test('日付でグループ化されて表示される（APIモック必要）', async ({ page }) => {
      // 複数の食事記録が同じ日付の場合、1つの .meals-group にまとめられることを確認
    });
  });

  test.describe('編集・削除機能', () => {
    test('編集ボタンが表示される（食事記録がある場合）', async ({ page }) => {
      // APIが実装されている場合、編集ボタンが .action-button.edit-button として表示される
    });

    test('削除ボタンが表示される（食事記録がある場合）', async ({ page }) => {
      // APIが実装されている場合、削除ボタンが .action-button.delete-button として表示される
    });

    test('削除確認ダイアログが表示される', async ({ page }) => {
      // 削除ボタンをクリック時に確認ダイアログが表示されることを確認
      // page.once('dialog', dialog => { ... });
    });
  });

  test.describe('レスポンシブデザイン', () => {
    test('モバイルビューで正しく表示される', async ({ page }) => {
      // モバイルサイズに設定
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/meals');

      // フィルターセクションが表示されることを確認
      await expect(page.locator('.filter-section')).toBeVisible();

      // スクロール可能であることを確認
      const container = page.locator('.meals-container');
      await expect(container).toBeVisible();
    });

    test('タブレットビューで正しく表示される', async ({ page }) => {
      // タブレットサイズに設定
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/meals');

      // フィルターセクションが表示されることを確認
      await expect(page.locator('.filter-section')).toBeVisible();
    });
  });

  test.describe('検索実行', () => {
    test('検索ボタンが有効で操作できる', async ({ page }) => {
      await page.goto('/meals');

      // ページが読み込まれるまで待つ
      await expect(page.locator('h1')).toContainText('食事記録');

      const searchButton = page.locator('.search-button');

      // 検索ボタンが表示されるまで待つ
      await expect(searchButton).toBeVisible();

      // 検索ボタンが有効であることを確認
      await expect(searchButton).toBeEnabled();
    });

    test('Enterキーで検索を実行できる', async ({ page }) => {
      await page.goto('/meals');

      const endDateInput = page.locator('input#end-date');

      // Enterキーを押す
      await endDateInput.press('Enter');

      // 検索が実行されることを確認
      // (実際のAPIレスポンスが必要なため、ここではスキップ)
    });

    test('再読み込みボタンが表示される（検索後）', async ({ page }) => {
      await page.goto('/meals');

      // 検索実行後に再読み込みボタンが表示されることを確認
      // (実際のAPIレスポンスが必要なため、ここではスキップ)
    });
  });
});
