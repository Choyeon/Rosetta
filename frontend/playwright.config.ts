import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E (Smoke) 配置。
 *
 * CI 默认：
 *   pnpm build && pnpm preview --port 4173 &
 *   BASE_URL=http://localhost:4173 pnpm test:e2e
 * 本地开发：
 *   pnpm dev 开着时 → BASE_URL=http://localhost:3000 pnpm test:e2e
 */
const baseURL = process.env.BASE_URL || 'http://localhost:3000'
const ciFullyParallel = !!process.env.CI

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: ciFullyParallel,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } }
    // 默认只跑 Chromium smoke；想扩浏览器取消注释下两行：
    // { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    // { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
  webServer: process.env.PW_START_NUXT === '1'
    ? {
        command: 'pnpm build && pnpm preview --port 4173',
        url: 'http://localhost:4173',
        reuseExistingServer: !ciFullyParallel,
        timeout: 300_000
      }
    : undefined
})
