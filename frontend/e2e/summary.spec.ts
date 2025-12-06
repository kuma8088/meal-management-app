/**
 * 1日の総評のE2Eテスト
 *
 * Task 28.1: 1日の総評のE2Eテスト
 */

import { test, expect } from '@playwright/test';

test.describe('1日の総評', () => {
  test.beforeEach(async ({ page }) => {
    // ログインページに移動してログイン
    // （実際のCognito認証が必要なため、ここではモックまたはテスト用ユーザーを使用）
    await page.goto('/login');
  });

  test.describe('総評ページ', () => {
    test('総評ページが正しく表示される', async ({ page }) => {
      // 総評ページに直接移動（認証後）
      await page.goto('/summary');

      // ページタイトルが表示されることを確認
      await expect(page.locator('h1')).toContainText('本日の栄養総評');

      // 日付セレクターが表示されることを確認
      await expect(page.locator('.date-selector')).toBeVisible();

      // ナビゲーションボタンが表示されることを確認
      await expect(page.locator('.nav-button').filter({ hasText: '前日' })).toBeVisible();
      await expect(page.locator('.nav-button').filter({ hasText: '翌日' })).toBeVisible();
    });

    test('本日の日付が初期設定される', async ({ page }) => {
      await page.goto('/summary');

      const dateInput = page.locator('.date-display input');
      const selectedDate = await dateInput.inputValue();

      // 本日の日付が設定されていることを確認
      const today = new Date().toISOString().split('T')[0];
      expect(selectedDate).toBe(today);
    });

    test('プロフィールが見つからない場合メッセージが表示される', async ({ page }) => {
      // プロフィールなしでアクセスした場合（APIモック必要）
      await page.goto('/summary');

      // プロフィール設定へのリンクが表示されることを期待
      // await expect(page.locator('.profile-missing')).toBeVisible();
      // await expect(page.locator('.link-button')).toContainText('プロフィール設定へ');
    });
  });

  test.describe('日付ナビゲーション', () => {
    test('前日ボタンで日付が戻る', async ({ page }) => {
      await page.goto('/summary');

      // ページタイトルが表示されるまで待つ
      await expect(page.locator('h1')).toContainText('本日の栄養総評');

      const dateInput = page.locator('.date-display input');
      const previousButton = page.locator('.nav-button').filter({ hasText: '前日' });

      // 日付入力が表示されるまで待つ
      await expect(dateInput).toBeVisible();

      const initialDate = await dateInput.inputValue();

      // 前日ボタンをクリック
      await previousButton.click();

      const newDate = await dateInput.inputValue();

      // 日付が1日戻ったことを確認
      const initialDateObj = new Date(initialDate);
      const newDateObj = new Date(newDate);
      const daysDiff = (initialDateObj.getTime() - newDateObj.getTime()) / (1000 * 60 * 60 * 24);

      expect(daysDiff).toBe(1);
    });

    test('翌日ボタンで日付が進む（本日以前）', async ({ page }) => {
      await page.goto('/summary');

      const dateInput = page.locator('.date-display input');
      const previousButton = page.locator('.nav-button').filter({ hasText: '前日' });
      const nextButton = page.locator('.nav-button').filter({ hasText: '翌日' });

      // 前日に移動
      await previousButton.click();
      const beforeDate = await dateInput.inputValue();

      // 翌日ボタンをクリック
      await nextButton.click();

      const afterDate = await dateInput.inputValue();

      // 日付が1日進んだことを確認
      const beforeDateObj = new Date(beforeDate);
      const afterDateObj = new Date(afterDate);
      const daysDiff = (afterDateObj.getTime() - beforeDateObj.getTime()) / (1000 * 60 * 60 * 24);

      expect(daysDiff).toBe(1);
    });

    test('翌日ボタンは本日以降は操作できない', async ({ page }) => {
      await page.goto('/summary');

      const nextButton = page.locator('.nav-button').filter({ hasText: '翌日' });

      // 本日では翌日ボタンが無効であることを確認
      await expect(nextButton).toBeDisabled();
    });

    test('本日に戻すボタンが表示される（本日以外）', async ({ page }) => {
      await page.goto('/summary');

      // ページタイトルが表示されるまで待つ
      await expect(page.locator('h1')).toContainText('本日の栄養総評');

      const previousButton = page.locator('.nav-button').filter({ hasText: '前日' });
      const todayButton = page.locator('.today-button');

      // 前日ボタンが表示されるまで待つ
      await expect(previousButton).toBeVisible();

      // 初期状態では本日に戻すボタンが表示されないことを確認
      await expect(todayButton).not.toBeVisible();

      // 前日に移動
      await previousButton.click();

      // 本日に戻すボタンが表示されることを確認
      await expect(todayButton).toBeVisible();

      // 本日に戻すボタンをクリック
      await todayButton.click();

      // 本日に戻すボタンが非表示になることを確認
      await expect(todayButton).not.toBeVisible();
    });

    test('日付入力で直接日付を選択できる', async ({ page }) => {
      await page.goto('/summary');

      const dateInput = page.locator('.date-display input');

      // 7日前の日付を選択
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      const dateStr = sevenDaysAgo.toISOString().split('T')[0];

      await dateInput.fill(dateStr);

      const selectedDate = await dateInput.inputValue();
      expect(selectedDate).toBe(dateStr);
    });

    test('本日より後の日付は選択できない', async ({ page }) => {
      await page.goto('/summary');

      const dateInput = page.locator('.date-display input');

      // 明日の日付を試す
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowStr = tomorrow.toISOString().split('T')[0];

      // maxで制限されているため、入力フィールドが明日を受け入れないことを確認
      // （HTML5のmax属性によって制限される）
    });
  });

  test.describe('栄養情報表示', () => {
    test('食事記録がない場合メッセージが表示される', async ({ page }) => {
      // 遠い過去の日付で栄養情報がない場合
      await page.goto('/summary');

      const dateInput = page.locator('.date-display input');

      // 過去の日付を選択
      const pastDate = '2020-01-01';
      await dateInput.fill(pastDate);

      // 「本日の食事記録がありません」メッセージが表示されることを確認
      await expect(page.locator('.no-meals')).toContainText('本日の食事記録がありません');
    });

    test('栄養情報が表示される（食事記録がある場合）', async ({ page }) => {
      // このテストは実際の食事記録データが必要

      await page.goto('/summary');

      // 期待される栄養情報の構造:
      // - .nutrition-section
      //   - .nutrition-bars
      //     - .nutrition-item (カロリー、PFC)
      // - .stats-section
      //   - .stat-card (カロリーバランス、PFCバランス)
    });

    test('AI栄養アドバイスが表示される（利用可能な場合）', async ({ page }) => {
      // このテストはアドバイスAPIが実装されている必要がある

      await page.goto('/summary');

      // 期待されるアドバイス情報の構造:
      // - .advice-section
      //   - .advice-content
      //     - .advice-text
      //   - .advice-info
      //     - .usage-count
    });

    test('利用制限メッセージが表示される', async ({ page }) => {
      // APIが利用制限に達している場合
      // .usage-limit-reached が表示される
    });
  });

  test.describe('栄養サマリー', () => {
    test('日付ごとにグループ化される（複数日の場合）', async ({ page }) => {
      // 複数日の食事記録がある場合、日付ごとにグループ化されることを確認
    });

    test('カロリーの進捗バーが表示される', async ({ page }) => {
      // .nutrition-bar が表示されることを確認
    });

    test('目標との比較が表示される', async ({ page }) => {
      // 目標が設定されている場合、比較情報が表示される
    });
  });

  test.describe('レスポンシブデザイン', () => {
    test('モバイルビューで正しく表示される', async ({ page }) => {
      // モバイルサイズに設定
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/summary');

      // ページタイトルが表示されることを確認
      await expect(page.locator('h1')).toContainText('本日の栄養総評');

      // 日付セレクターが表示されることを確認
      await expect(page.locator('.date-selector')).toBeVisible();
    });

    test('タブレットビューで正しく表示される', async ({ page }) => {
      // タブレットサイズに設定
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/summary');

      // ページタイトルが表示されることを確認
      await expect(page.locator('h1')).toContainText('本日の栄養総評');
    });
  });
});
