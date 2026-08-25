const pc = require('D:/WebProjects/Rosetta/frontend/node_modules/.pnpm/playwright-core@1.62.1/node_modules/playwright-core')
const { chromium } = pc
(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage()
  const errs = []
  page.on('console', m => {
    const t = m.text()
    if (t.includes('app:error') || t.includes('Must be called at the top')) errs.push(t.slice(0, 220))
  })
  page.on('pageerror', e => errs.push('PE:' + (e.stack || e.message).slice(0, 300)))
  await page.goto('http://127.0.0.1:3000/', { waitUntil: 'networkidle', timeout: 20000 })
  await page.waitForTimeout(1000)
  const navs = ['/tags', '/categories', '/about', '/search?q=test', '/', '/admin/login', '/']
  for (const n of navs) {
    const clicked = await page.evaluate((url) => {
      const a = Array.from(document.querySelectorAll('a')).find(el => el.getAttribute('href') === url)
      if (a) { a.click(); return true }
      return false
    }, n)
    if (!clicked) { await page.goto('http://127.0.0.1:3000' + n, { waitUntil: 'networkidle' }).catch(() => {}) }
    await page.waitForTimeout(1000)
  }
  console.log('NAV ERRORS (' + errs.length + '):')
  console.log(errs.join('\n'))
  await browser.close()
})().catch(e => { console.error('ERR', e.message); process.exit(1) })
