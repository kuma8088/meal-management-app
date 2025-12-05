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

  console.log('ログイン成功 - 認証状態を保存中...');

  // 認証状態を保存
  await page.context().storageState({ path: authFile });

  console.log('認証状態を保存しました:', authFile);
});
