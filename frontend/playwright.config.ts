import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright設定
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  globalSetup: './tests/global-setup.ts',
  globalTeardown: './tests/global-teardown.ts',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    // セットアッププロジェクト: テストユーザーでログインして認証状態を保存
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    // 認証なしテスト（ログイン・ユーザー登録など）
    {
      name: 'chromium-unauthenticated',
      testMatch: /.*\/auth\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['setup'], // テストユーザーの作成は必要
    },

    // 認証が必要なテスト
    {
      name: 'chromium',
      testIgnore: /.*\/auth\.spec\.ts/, // auth.spec.tsは除外
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],

  webServer: {
    command: 'vite --mode test',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
