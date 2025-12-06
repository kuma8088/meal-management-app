/**
 * 認証セットアップ
 * テストユーザーでログインして認証状態を保存
 */

import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  // ログインページに移動
  await page.goto('/login');

  // テストユーザーの認証情報を環境変数から取得
  const username = process.env.E2E_TEST_USERNAME || 'e2e-test@example.com';
  const password = process.env.E2E_TEST_PASSWORD || 'TestPassword123!';

  console.log('テストユーザーでログイン中:', username);

  // ログインフォームに入力
  await page.locator('input#username').fill(username);
  await page.locator('input#password').fill(password);

  // ログインボタンをクリック
  await page.locator('button[type="submit"]:has-text("ログイン")').click();

  // ログイン成功を待機（ホームページへのリダイレクト）
  await page.waitForURL('/');

  // ログイン成功の確認
  await expect(page.locator('text=ようこそ')).toBeVisible({ timeout: 10000 });

  console.log('ログイン成功 - プロフィールを作成中...');

  // テスト用のプロフィールを作成（APIを直接呼び出し）
  const apiBaseUrl = process.env.VITE_API_BASE_URL || 'http://localhost:3000';

  try {
    // プロフィール作成APIを呼び出し
    await page.evaluate(async (apiUrl) => {
      const response = await fetch(`${apiUrl}/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('idToken')}`,
        },
        body: JSON.stringify({
          age: 30,
          gender: 'male',
          height: 170,
          weight: 70,
          activity_level: 'moderate',
        }),
      });

      if (!response.ok && response.status !== 409) {
        // 409 (Conflict) = 既に存在する場合は無視
        throw new Error(`Failed to create profile: ${response.status}`);
      }

      return response.json();
    }, apiBaseUrl);

    console.log('プロフィールを作成しました');
  } catch (error: any) {
    // プロフィール作成失敗は警告のみ（既に存在する可能性）
    console.warn('プロフィール作成の警告:', error.message);
  }

  console.log('認証状態を保存中...');

  // 認証状態を保存
  await page.context().storageState({ path: authFile });

  console.log('認証状態を保存しました:', authFile);
});
