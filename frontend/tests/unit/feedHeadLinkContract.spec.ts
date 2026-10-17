/**
 * RSS / Sitemap `<link>` 单源契约。
 *
 * 表现过的 bug：开关在后台关掉后 `/rss.xml` 已经回 404，但 `<head>` 里仍然挂着
 * `rel=alternate type=application/rss+xml` 和 `rel=sitemap`——因为 nuxt.config.ts 的
 * `app.head.link` 是**构建期常量**，读不到运行期的 features 分组。爬虫据此承诺的入口
 * 全是空壳，等于让"关掉订阅源"这个设置静默失效。
 *
 * 因此：head 里这两个 link 只能有一个来源，就是 layouts/default.vue 里按
 * `site.features` 条件输出的那一份。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const nuxtConfig = readFileSync(resolve(process.cwd(), 'nuxt.config.ts'), 'utf8')
const defaultLayout = readFileSync(resolve(process.cwd(), 'layouts/default.vue'), 'utf8')

describe('RSS / Sitemap head link 只允许运行期条件输出', () => {
  it('nuxt.config.ts 的静态 head 不得硬挂 feed / sitemap link', () => {
    // 整文件匹配即可：routeRules 里的 `'Content-Type': 'application/rss+xml'` 是响应头，
    // 不带 `rel:`，不会被下面两条正则命中。
    expect(nuxtConfig, '构建期 head 读不到 features 开关，不得输出 rss link')
      .not.toMatch(/rel:\s*'alternate'[^\n]*application\/rss\+xml/)
    expect(nuxtConfig, '构建期 head 读不到 features 开关，不得输出 sitemap link')
      .not.toMatch(/rel:\s*'sitemap'/)
    expect(nuxtConfig).toContain('head:')
  })

  it('layouts/default.vue 必须按 features 开关条件输出两条 link', () => {
    expect(defaultLayout).toMatch(/f\.enable_rss\s*\?\s*\[\{ rel: 'alternate', type: 'application\/rss\+xml'/)
    expect(defaultLayout).toMatch(/f\.enable_sitemap\s*\?\s*\[\{ rel: 'sitemap'/)
    expect(defaultLayout, '两条 link 的判定源必须是 site.features 而不是别处常量')
      .toContain('site.features.value')
  })
})
