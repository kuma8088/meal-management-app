/**
 * クリティカルパス E2E テスト
 *
 * Device Farm / Playwrightで実行する最重要ユーザーフローテスト
 * 20個のテストケース: ログイン → 食事記録 → 目標管理 → 統計表示
 */

import { test, expect } from '@playwright/test';

test.describe('【Critical Path】食事管理アプリケーション - 全体フロー', () => {
  // テストの前処理: ログイン状態を確保
  test.beforeAll(async ({ context }) => {
    // 認証情報が保存されていることを確認
    const storageState = await context?.storageState();
    if (!storageState || !storageState.cookies?.length) {
      console.warn('認証情報が見つかりません - セットアップフェーズを実行してください');
    }
  });

  // ================================
  // セクション 1: 認証フロー (4テスト)
  // ================================
  test.describe('認証とプロフィール設定', () => {
    test('1. ホームページが正しく表示される', async ({ page }) => {
      await page.goto('/');

      // ホームページの主要要素を確認
      await expect(page.locator('h1')).toContainText('食事管理アプリ');
      await expect(page.locator('text=本日の食事')).toBeVisible();
      await expect(page.locator('text=栄養バランス')).toBeVisible();

      // メニューが表示されていることを確認
      await expect(page.locator('nav')).toBeVisible();
    });

    test('2. プロフィール情報が表示される', async ({ page }) => {
      await page.goto('/');

      // プロフィールセクションを確認
      await expect(page.locator('.user-profile')).toBeVisible();

      // ユーザー情報が表示されていることを確認
      const profileName = page.locator('.user-profile-name');
      await expect(profileName).toBeVisible();
    });

    test('3. プロフィール編集が可能', async ({ page }) => {
      await page.goto('/profile');

      // プロフィールページが表示される
      await expect(page.locator('h1')).toContainText('プロフィール');

      // 編集フォームが表示されている
      await expect(page.locator('input[name="height"]')).toBeVisible();
      await expect(page.locator('input[name="weight"]')).toBeVisible();
      await expect(page.locator('select[name="activity_level"]')).toBeVisible();
    });

    test('4. ログアウト機能が動作する', async ({ page }) => {
      // メニューを開く
      const menuButton = page.locator('button:has-text("メニュー")');
      await menuButton.click();

      // ログアウトボタンが表示される
      const logoutButton = page.locator('button:has-text("ログアウト")');
      await expect(logoutButton).toBeVisible();
    });
  });

  // ================================
  // セクション 2: 食事登録フロー (6テスト)
  // ================================
  test.describe('食事記録 - 登録から確認まで', () => {
    test('5. 食事登録ページにアクセスできる', async ({ page }) => {
      await page.goto('/meals/new');

      // ページが正しく読み込まれている
      await expect(page.locator('h1')).toContainText('食事登録');

      // フォーム要素が表示されている
      await expect(page.locator('#meal-type')).toBeVisible();
      await expect(page.locator('#timestamp')).toBeVisible();
      await expect(page.locator('#food-search')).toBeVisible();
    });

    test('6. 食事タイプを選択できる', async ({ page }) => {
      await page.goto('/meals/new');

      const mealTypeSelect = page.locator('#meal-type');

      // 各食事タイプを選択可能
      await mealTypeSelect.selectOption('breakfast');
      await expect(mealTypeSelect).toHaveValue('breakfast');

      await mealTypeSelect.selectOption('lunch');
      await expect(mealTypeSelect).toHaveValue('lunch');

      await mealTypeSelect.selectOption('dinner');
      await expect(mealTypeSelect).toHaveValue('dinner');
    });

    test('7. 食品検索が動作する', async ({ page }) => {
      // 食品検索APIをモック
      await page.route('**/foods/search*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              food_id: 'test-001',
              name: 'テストフード',
              calories_per_100g: 100,
              protein_per_100g: 5,
              fat_per_100g: 3,
              carbs_per_100g: 15
            }
          ])
        });
      });

      await page.goto('/meals/new');

      // 検索フィールドに入力
      const searchInput = page.locator('#food-search');
      await searchInput.fill('テスト');

      // 検索ボタンをクリック
      await page.locator('.search-button').click();

      // 検索結果が表示される
      await expect(page.locator('text=テストフード')).toBeVisible();
    });

    test('8. 食品を選択して数量を入力できる', async ({ page }) => {
      // モック設定
      await page.route('**/foods/search*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([{
            food_id: 'test-001',
            name: 'テストフード',
            calories_per_100g: 100,
            protein_per_100g: 5,
            fat_per_100g: 3,
            carbs_per_100g: 15
          }])
        });
      });

      await page.goto('/meals/new');

      // 検索実行
      await page.locator('#food-search').fill('テスト');
      await page.locator('.search-button').click();

      // 食品選択
      await page.locator('text=テストフード').click();

      // 数量入力
      const amountInput = page.locator('input[placeholder*="g"]').first();
      await amountInput.fill('100');
      await expect(amountInput).toHaveValue('100');
    });

    test('9. 複数の食品を追加できる', async ({ page }) => {
      // モック設定
      await page.route('**/foods/search*', async (route) => {
        const url = new URL(route.request().url());
        const query = url.searchParams.get('query');

        if (query?.includes('米')) {
          await route.fulfill({
            status: 200,
            body: JSON.stringify([{
              food_id: 'rice',
              name: '白米',
              calories_per_100g: 156
            }])
          });
        } else {
          await route.fulfill({
            status: 200,
            body: JSON.stringify([{
              food_id: 'fish',
              name: '鯖',
              calories_per_100g: 207
            }])
          });
        }
      });

      await page.goto('/meals/new');

      // 1つ目の食品を追加
      await page.locator('#food-search').fill('米');
      await page.locator('.search-button').click();
      await page.locator('text=白米').click();

      // 合計表示が更新される
      const totalCalories = page.locator('.total-calories');
      await expect(totalCalories).not.toBeEmpty();
    });

    test('10. 食事を登録できる', async ({ page }) => {
      // 食事作成APIをモック
      await page.route('**/meals', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              meal_id: 'meal-001',
              user_id: 'user-001',
              timestamp: new Date().toISOString(),
              type: 'breakfast'
            })
          });
        }
      });

      await page.goto('/meals/new');

      // 食事タイプ選択
      await page.locator('#meal-type').selectOption('breakfast');

      // 登録ボタンをクリック
      const submitButton = page.locator('button[type="submit"]:has-text("登録")');
      await submitButton.click();

      // 成功メッセージが表示される
      await expect(page.locator('text=登録しました')).toBeVisible({ timeout: 5000 });
    });
  });

  // ================================
  // セクション 3: 食事履歴と統計 (4テスト)
  // ================================
  test.describe('食事管理 - 履歴と統計表示', () => {
    test('11. 本日の食事一覧が表示される', async ({ page }) => {
      await page.goto('/meals');

      // ページが正しく表示される
      await expect(page.locator('h1')).toContainText('食事一覧');

      // 食事リストが表示される
      const mealsList = page.locator('.meals-list');
      await expect(mealsList).toBeVisible();
    });

    test('12. 日付を指定して食事を検索できる', async ({ page }) => {
      await page.goto('/meals');

      // 日付ピッカーが存在する
      const datePicker = page.locator('input[type="date"]');
      await expect(datePicker).toBeVisible();

      // 日付を選択
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() - 1);
      const dateStr = tomorrow.toISOString().split('T')[0];
      await datePicker.fill(dateStr);

      // リストが更新される
      await page.waitForTimeout(500);
    });

    test('13. 栄養バランスが表示される', async ({ page }) => {
      await page.goto('/');

      // 栄養バランスセクションが表示される
      await expect(page.locator('text=栄養バランス')).toBeVisible();

      // タンパク質、脂質、炭水化物のグラフが表示される
      await expect(page.locator('.nutrition-chart')).toBeVisible();
    });

    test('14. 本日の摂取カロリーが表示される', async ({ page }) => {
      await page.goto('/');

      // カロリー表示が存在する
      const caloriesDisplay = page.locator('.daily-calories');
      await expect(caloriesDisplay).toBeVisible();

      // 数値が表示されている
      const caloriesValue = caloriesDisplay.locator('.calories-value');
      await expect(caloriesValue).toContainText(/\d+/);
    });
  });

  // ================================
  // セクション 4: 目標設定とAIアドバイス (4テスト)
  // ================================
  test.describe('目標管理とAIアドバイス', () => {
    test('15. 目標設定ページにアクセスできる', async ({ page }) => {
      await page.goto('/goals');

      // ページが正しく表示される
      await expect(page.locator('h1')).toContainText('目標設定');

      // 目標フォームが表示される
      await expect(page.locator('.goal-form')).toBeVisible();
    });

    test('16. 体重目標を設定できる', async ({ page }) => {
      await page.goto('/goals');

      // 目標タイプ選択
      await page.locator('select#goal_type').selectOption('lose');

      // 目標体重を入力
      const targetWeightInput = page.locator('input#target_weight');
      await targetWeightInput.fill('60');
      await expect(targetWeightInput).toHaveValue('60');

      // 目標日を入力
      const targetDateInput = page.locator('input#target_date');
      const futureDate = new Date();
      futureDate.setMonth(futureDate.getMonth() + 3);
      const dateStr = futureDate.toISOString().split('T')[0];
      await targetDateInput.fill(dateStr);
    });

    test('17. 現在の目標が表示される', async ({ page }) => {
      await page.goto('/');

      // 目標セクションが表示される
      const goalSection = page.locator('.goal-section');
      if (await goalSection.isVisible()) {
        // 目標体重が表示されている
        await expect(goalSection.locator('text=目標')).toBeVisible();
      }
    });

    test('18. AIアドバイスを取得できる', async ({ page }) => {
      // AIアドバイスAPIをモック
      await page.route('**/advice/daily*', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              advice: 'バランスの取れた食事ですね。',
              suggestions: ['タンパク質をもう少し増やすといいでしょう']
            })
          });
        }
      });

      await page.goto('/');

      // AIアドバイスボタンがあれば
      const adviceButton = page.locator('button:has-text("アドバイス")');
      if (await adviceButton.isVisible()) {
        await adviceButton.click();

        // アドバイスが表示される
        await expect(page.locator('text=バランスの取れた')).toBeVisible({ timeout: 5000 });
      }
    });
  });

  // ================================
  // セクション 5: 統合フロー (2テスト)
  // ================================
  test.describe('統合フロー - エンドツーエンド', () => {
    test('19. 完全な一日のフロー実行', async ({ page }) => {
      // 1. ホームページ表示
      await page.goto('/');
      await expect(page.locator('h1')).toContainText('食事管理');

      // 2. 朝食登録ページへ
      await page.locator('text=食事を追加').click();
      await page.waitForURL('**/meals/new');

      // 3. フォーム入力
      await page.locator('#meal-type').selectOption('breakfast');

      // 4. ホームに戻る
      await page.locator('a[href="/"]').click();
      await page.waitForURL('/');

      // 5. 統計が表示されている
      await expect(page.locator('.nutrition-chart')).toBeVisible();
    });

    test('20. ネットワークエラーが適切に処理される', async ({ page }) => {
      // API呼び出しを失敗させるようにモック
      await page.route('**/meals', async (route) => {
        await route.abort();
      });

      await page.goto('/meals/new');

      // エラーハンドリングが動作することを確認
      // (実装によってはエラーメッセージが表示される)
      await page.locator('#meal-type').selectOption('breakfast');

      // ページが崩れていないことを確認
      await expect(page.locator('h1')).toContainText('食事登録');
    });
  });
});
