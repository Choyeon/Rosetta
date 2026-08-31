// Admin routes smoke test using Playwright
// Visits all /admin/* routes, captures console errors and Nuxt app:error,
// reports per-route status.

import { chromium } from '@playwright/test'

const BASE = 'http://localhost:3000'

// All admin routes to smoke test
const ROUTES = [
  '/admin',
  '/admin/content/posts',
  '/admin/content/posts/new',
  '/admin/content/categories',
  '/admin/content/tags',
  '/admin/content/series',
  '/admin/content/pages',
  '/admin/interaction/comments',
  '/admin/interaction/guestbook',
  '/admin/interaction/activities',
  '/admin/interaction/announcements',
  '/admin/users',
  '/admin/users/titles',
  '/admin/media/library',
  '/admin/media/gallery',
  '/admin/system/settings',
  '/admin/system/navigation',
  '/admin/system/friendlinks',
  '/admin/system/webhooks',
  '/admin/tools/audit-logs',
  '/admin/tools/cache',
  '/admin/tools/import-export',
  '/admin/tools/migrations',
  '/admin/tools/performance',
  '/admin/tools/seo',
  '/admin/tools/translate'
]

async function main() {
  const browser = await chromium.launch()
  const results = []

  // Two-pass strategy: pass 1 warms up on-demand route compilation on the dev
  // server (first visit to each route triggers Vite compile); pass 2 verifies.
  for (let pass = 1; pass <= 2; pass++) {
    const isVerify = pass === 2
    for (const route of ROUTES) {
      const context = await browser.newContext()
      const page = await context.newPage()

      const consoleErrors = []
      const pageErrors = []
      const appErrors = []

      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text())
      })
      page.on('pageerror', err => pageErrors.push(err.message))
      page.on('vue:error', err => appErrors.push(err.message))

      let status = 'OK'
      let httpStatus = 'unknown'
      let renderState = 'unknown'
      try {
        const resp = await page.goto(BASE + route, {
          waitUntil: 'domcontentloaded',
          timeout: 45000
        })
        httpStatus = resp ? resp.status() : 'no-response'

        // Wait for the app to mount (first-visit routes compile on demand)
        try {
          await page.waitForSelector('#__nuxt', { timeout: 30000 })
        } catch {
          // retry once: route may still be compiling
          await page.waitForSelector('#__nuxt', { timeout: 30000 })
        }
        // Give client hydration + onMounted fetches time to settle
        await page.waitForTimeout(2000)

        // Classify what actually rendered
        renderState = await page.evaluate(() => {
          if (document.querySelector('nuxt-error-page')
            || document.querySelector('[data-fatal-error]')
            || document.body.textContent?.includes('Internal Server Error')
            || document.body.textContent?.includes('Application error')) {
            return 'APP_ERROR'
          }
          // Login screen (auth-gated routes) is a valid render
          if (document.body.textContent?.includes('登录')
            || document.body.textContent?.includes('输入账号信息以继续')) {
            return 'LOGIN'
          }
          if ((document.body?.innerText?.length || 0) > 20) return 'RENDERED'
          return 'EMPTY'
        })
        if (renderState === 'APP_ERROR' || renderState === 'EMPTY') status = 'APP_ERROR'
      } catch (e) {
        status = 'NAV_FAIL'
        pageErrors.push(String(e).slice(0, 200))
      }

      // Filter out benign errors (e.g. favicon 404 in dev, HMR)
      const realConsoleErrors = consoleErrors.filter(e =>
        !e.includes('favicon')
        && !e.includes('[vite]')
        && !e.toLowerCase().includes('net::err_aborted')
        && !e.toLowerCase().includes('err_connection_closed')
      )

      if (isVerify) {
        results.push({
          route,
          status,
          httpStatus,
          renderState,
          consoleErrors: realConsoleErrors,
          pageErrors,
          appErrors
        })
      }

      await context.close()
      // Brief breather so the dev server isn't slammed with parallel compiles
      await new Promise(r => setTimeout(r, 400))
    }
    if (!isVerify) console.log(`[pass ${pass}] warmup complete`)
  }

  await browser.close()

  // Report
  console.log('\n=== ADMIN SMOKE TEST RESULTS ===\n')
  let failCount = 0
  for (const r of results) {
    // A route is "clean" if it rendered (RENDERED/LOGIN) with no JS errors.
    // LOGIN = auth-gated, app correctly redirected to login screen.
    const hasIssues = r.status !== 'OK' || r.consoleErrors.length > 0
      || r.pageErrors.length > 0 || r.appErrors.length > 0
    if (hasIssues) failCount++
    const flag = hasIssues ? '❌' : '✅'
    console.log(`${flag} ${r.route} [${r.status}] HTTP:${r.httpStatus} state:${r.renderState}`)
    if (r.consoleErrors.length) console.log('   console:', r.consoleErrors.slice(0, 3))
    if (r.pageErrors.length) console.log('   pageerror:', r.pageErrors.slice(0, 3))
    if (r.appErrors.length) console.log('   apperror:', r.appErrors.slice(0, 3))
  }
  console.log(`\n${results.length - failCount}/${results.length} routes clean`)
  process.exit(failCount > 0 ? 1 : 0)
}

main().catch((e) => {
  console.error('Smoke test crashed:', e)
  process.exit(2)
})
