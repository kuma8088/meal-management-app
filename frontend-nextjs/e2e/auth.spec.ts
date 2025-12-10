import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test('should redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/')
    await page.waitForURL('/login')
    expect(page.url()).toContain('/login')
  })

  test('should display login page with Cognito button', async ({ page }) => {
    await page.goto('/login')
    const cognitoButton = page.getByRole('button', { name: /Cognito でログイン/i })
    await expect(cognitoButton).toBeVisible()
  })

  test('should display error page when navigating to /auth/error', async ({ page }) => {
    await page.goto('/auth/error')
    const heading = page.getByRole('heading', { name: /認証エラー/i })
    await expect(heading).toBeVisible()
  })

  test('should have correct meta tags for SEO', async ({ page }) => {
    await page.goto('/login')

    const description = page.locator('meta[name="description"]')
    await expect(description).toHaveAttribute(
      'content',
      /AI を活用した食事管理アプリ/
    )

    const ogTitle = page.locator('meta[property="og:title"]')
    await expect(ogTitle).toHaveAttribute('content', /食事管理アプリ/)
  })
})

test.describe('Navigation', () => {
  test('should have correct lang attribute', async ({ page }) => {
    await page.goto('/login')
    const html = page.locator('html')
    await expect(html).toHaveAttribute('lang', 'ja')
  })

  test('should preload external resources', async ({ page }) => {
    await page.goto('/login')

    const preconnects = await page.locator('link[rel="preconnect"]').count()
    expect(preconnects).toBeGreaterThan(0)
  })
})
