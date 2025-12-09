import { defineConfig, devices } from '@playwright/test';

/**
 * Device Farm 用 Playwright 設定（スモークテスト専用）
 *
 * デプロイ済みの CloudFront URL に対してテストを実行
 * - webServer セクションなし（ローカルサーバー起動不要）
 * - globalSetup なし（認証不要のスモークテストのみ実行）
 * - baseURL は環境変数で設定可能
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: true,
  retries: 2,
  workers: 1,
  reporter: [['html'], ['junit', { outputFile: 'test-results/junit.xml' }]],
  // スモークテストは認証不要のため globalSetup/Teardown なし
  use: {
    // 環境変数 BASE_URL を使用、デフォルトは CloudFront URL
    baseURL: process.env.BASE_URL || 'https://d2b7c2gzuy0hmt.cloudfront.net',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    // タイムアウト設定
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },

  // タイムアウト設定
  timeout: 60000,
  expect: {
    timeout: 10000,
  },

  projects: [
    // スモークテスト用（認証なし）
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],

  // webServer セクションなし - デプロイ済みアプリをテスト
});
