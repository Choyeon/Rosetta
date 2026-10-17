/**
 * SSR HTML 的 `Cache-Control` 必须让浏览器回源校验（`max-age=0`），
 * 否则回访访客会复用磁盘里的旧 HTML —— 站点设置烘在 `__NUXT_DATA__` payload 里，
 * `useSite` 客户端看到 `loaded=true` 就不会再拉 `/api/settings/public`，
 * 表现是"后台改了、前台不生效"（实测 `navigation[0].transferSize === 0`）。
 *
 * 归一函数必须幂等且只碰带 s-maxage 的 HTML 响应：
 * `no-store`（后台/登录/搜索）与 `/_nuxt/**` 强缓存静态资源一律不得被改写。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { normalizeHtmlCacheControl } from '../../server/utils/ssrHtmlCacheControl'

const ROOT = resolve(__dirname, '..', '..')
const pluginSrc = readFileSync(
  resolve(ROOT, 'server/plugins/ssr-html-revalidate.nitro.ts'),
  'utf-8'
)

describe('normalizeHtmlCacheControl', () => {
  it('把 Nitro swr 的覆写补回文档口径（保留原 TTL）', () => {
    expect(normalizeHtmlCacheControl('s-maxage=600, stale-while-revalidate')).toBe(
      'public, max-age=0, s-maxage=600, stale-while-revalidate=86400'
    )
    expect(normalizeHtmlCacheControl('s-maxage=60, stale-while-revalidate=600')).toBe(
      'public, max-age=0, s-maxage=60, stale-while-revalidate=600'
    )
    // 裸形式回填必须按本页 s-maxage 档：热榜 60s 的窗口是 600，不是公开页默认的 86400
    expect(normalizeHtmlCacheControl('s-maxage=60, stale-while-revalidate')).toBe(
      'public, max-age=0, s-maxage=60, stale-while-revalidate=600'
    )
  })

  it('已合规的响应不改写（幂等，可被两道钩子双跑）', () => {
    const ok = 'public, max-age=0, s-maxage=300, stale-while-revalidate=86400'
    expect(normalizeHtmlCacheControl(ok)).toBeNull()
    const once = normalizeHtmlCacheControl('s-maxage=300, stale-while-revalidate=86400')
    expect(normalizeHtmlCacheControl(once)).toBeNull()
  })

  it('no-store / 强缓存静态资源 / 空值一律不动', () => {
    expect(normalizeHtmlCacheControl('no-store, private')).toBeNull()
    expect(normalizeHtmlCacheControl('public, max-age=31536000, immutable')).toBeNull()
    expect(normalizeHtmlCacheControl('')).toBeNull()
    expect(normalizeHtmlCacheControl(null)).toBeNull()
    expect(normalizeHtmlCacheControl(undefined)).toBeNull()
  })
})

describe('ssr-html-revalidate 插件接线', () => {
  it('复用同一个归一函数，且只处理 text/html', () => {
    expect(pluginSrc).toContain('normalizeHtmlCacheControl')
    expect(pluginSrc).toContain('ssrHtmlCacheControl')
    expect(pluginSrc).toContain('text/html')
  })

  it('Nitro 截断形态能还原回 routeRules 声明的口径', () => {
    expect(normalizeHtmlCacheControl('s-maxage=1800')).toBe('public, max-age=0, s-maxage=1800')
  })

  it('routeRules 里声明的公开页口径与归一产出同形（防两处各写一套）', () => {
    const nuxtConfig = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')
    const declared: string[] = [...nuxtConfig.matchAll(/'Cache-Control': '([^']+)'/g)]
      .map(m => m[1])
      .filter((v): v is string => Boolean(v))
    const swrPages = declared.filter(v => v.includes('s-maxage'))
    // 覆盖度自检：这条测试真的扫到公开页规则，而不是空集合静默通过
    expect(swrPages.length).toBeGreaterThan(3)
    for (const value of swrPages) {
      if (!value.includes('max-age=0')) {
        // 显式私有 max-age（媒体/静态资源）不属本页口径：归一函数必须不动它
        expect(normalizeHtmlCacheControl(value)).toBeNull()
        continue
      }
      const nitroForm = value
        .replace('public, max-age=0, ', '')
        .replace(/, stale-while-revalidate=\d+/, ', stale-while-revalidate')
      expect(normalizeHtmlCacheControl(nitroForm)).toBe(value)
    }
  })
})
