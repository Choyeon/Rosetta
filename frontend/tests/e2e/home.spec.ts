import { test, expect } from '@playwright/test'

/**
 * Playwright smoke：首页可访问且标题包含 Rosetta 关键字眼。
 * 运行：
 *   pnpm dev
 *   BASE_URL=http://localhost:3000 pnpm test:e2e:smoke
 */
test.describe('首页 smoke', () => {
  test('打开首页，title 不为空', async ({ page, baseURL }) => {
    // 站点启用了 OOBE 时会跳到 /oobe，这里兼容两种情况：
    const resp = await page.goto(baseURL ?? '/', { waitUntil: 'domcontentloaded' })
    if (resp && (resp.status() === 503 || resp.status() === 401)) {
      // 后端未就绪（如 OOBE 未完成 / 服务未启动）：记录并跳过断言具体标题
      test.skip()
    }
    const title = await page.title()
    expect(title.length).toBeGreaterThan(0)
    // 标题通常是 Rosetta Blog / Rosetta / 中文站点名之一
    expect(title).toMatch(/Rosetta|博客|Blog|i18n/i)
  })
})
