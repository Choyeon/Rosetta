/**
 * i18n prefix_except_default 下"URL 的语言变体"口径契约。
 *
 * 实测踩过的坑：canonical / hreflang / JSON-LD 的 URL 最初走 @nuxtjs/i18n 的
 * localePath(path, locale)。它按**路由名**解析传入字符串，详情页的
 * `/posts/{中文 slug}` 在 SSR 期产出过非字符串，asAbsolute 于是在
 * `path.startsWith` 上抛 TypeError —— 而这段跑在 useHead 的求值路径上，
 * 结果是**每一篇文章详情页整页 500**（旧构建因 siteUrl 为空串提前返回，
 * 把这个坑藏住了，配上 NUXT_PUBLIC_SITE_URL 才暴露）。
 *
 * 本仓 i18n 没有 per-locale 自定义路径，策略的全部含义就是
 * "默认语言裸路径 + 其余挂 /code 前缀"，所以 URL 派生改成纯字符串算术。
 * 这里同时钉住：不得再退回 localePath，且所有产出 URL 的地方共用同一个 helper。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  applyLocalePrefix,
  DEFAULT_LOCALE_CODE,
  HREFLANG_MAP,
  OG_LOCALE_MAP,
  stripLocalePrefix
} from '../../composables/useSeo'

const ROOT = resolve(__dirname, '..', '..')

describe('applyLocalePrefix / stripLocalePrefix', () => {
  it('默认语言裸路径，其它三语挂前缀', () => {
    expect(applyLocalePrefix('/posts/hello', DEFAULT_LOCALE_CODE)).toBe('/posts/hello')
    expect(applyLocalePrefix('/posts/hello', 'en')).toBe('/en/posts/hello')
    expect(applyLocalePrefix('/posts/hello', 'ja')).toBe('/ja/posts/hello')
    expect(applyLocalePrefix('/posts/hello', 'zh_Hant')).toBe('/zh_Hant/posts/hello')
  })

  it('首页前缀不带尾斜杠（/en 而不是 /en/）', () => {
    expect(applyLocalePrefix('/', 'en')).toBe('/en')
    expect(applyLocalePrefix('/', DEFAULT_LOCALE_CODE)).toBe('/')
  })

  it('入参已带语言前缀时先剥再挂，切换语言不会叠前缀', () => {
    expect(applyLocalePrefix('/en/posts/hello', 'ja')).toBe('/ja/posts/hello')
    expect(stripLocalePrefix('/zh_Hant/archive/2026/03')).toBe('/archive/2026/03')
    expect(stripLocalePrefix('/en')).toBe('/')
    // 不能被误伤：/encyclopedia 不是语言前缀
    expect(stripLocalePrefix('/encyclopedia')).toBe('/encyclopedia')
  })

  it('查询串与锚点留在末尾，不被前缀插进去', () => {
    expect(applyLocalePrefix('/posts?page=2', 'en')).toBe('/en/posts?page=2')
    expect(applyLocalePrefix('/posts/hello#comments', 'ja')).toBe('/ja/posts/hello#comments')
  })

  it('hreflang / og:locale 两张表覆盖全部四语（新增语言必须同步）', () => {
    const codes = Object.keys(HREFLANG_MAP)
    expect(codes).toEqual(Object.keys(OG_LOCALE_MAP))
    expect(codes).toContain(DEFAULT_LOCALE_CODE)
    expect(HREFLANG_MAP.zh_Hant).toBe('zh-Hant')
    expect(OG_LOCALE_MAP.zh_Hant).toBe('zh_TW')
  })
})

describe('URL 派生的单源约束（静态）', () => {
  const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')

  it('SEO 侧不再依赖 localePath（详情页 500 的成因）', () => {
    expect(seo).not.toContain('useLocalePath')
    expect(seo).toContain('applyLocalePrefix(')
  })

  it('canonical / hreflang 缺省 url 时按当前路径派生，且只保留分页参数', () => {
    expect(seo).toContain('CANONICAL_QUERY_KEYS')
    // 视图变体参数（search/category/sort）不得进 canonical
    expect(seo).not.toMatch(/CANONICAL_QUERY_KEYS = \[[^\]]*search/)
  })

  it('站点根在生产不接受请求 Host 推导（缓存投毒面）', () => {
    expect(seo).toContain('LOOPBACK_HOST_RE')
    expect(seo).not.toContain('x-forwarded-host')
  })

  it('详情页不再另写一份 canonical', () => {
    const page = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf-8')
    expect(page).not.toContain('useRequestURL')
    expect(page).toContain('article:publisher')
    expect(page).toContain('article:tag')
  })

  it('robots.txt 只挡机器面，语言前缀四份都要写', () => {
    const switcher = readFileSync(resolve(ROOT, 'components/LocaleSwitcher.vue'), 'utf-8')
    expect(switcher).not.toContain('useSwitchLocalePath')
    expect(switcher).toContain('applyLocalePrefix')

    const robots = readFileSync(resolve(ROOT, 'server/routes/robots.txt.get.ts'), 'utf-8')
    expect(robots).toContain('/zh_Hant')
    expect(robots).toContain('/admin/')
    // /login /register /account /search /oobe 必须由 Disallow 挪到页面 meta：
    // 抓不到就读不到 noindex，Google 会按已发现的链接生成"无摘要索引条目"。
    for (const moved of ['/login', '/register', '/account', '/search', '/oobe']) {
      expect(robots, `robots.txt 仍挡着 ${moved}，页面自带 noindex 就永远读不到`)
        .not.toContain(`'${moved}'`)
    }
  })

  it('不可索引页各自带 noindex 闸门（Disallow 不等于 noindex）', () => {
    const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')
    expect(seo).toContain('export function useNoindexPage')
    expect(seo).toContain('noindex, follow')
    for (const page of [
      'pages/login.vue',
      'pages/register.vue',
      'pages/forgot-password.vue',
      'pages/account/index.vue',
      'pages/account/settings.vue',
      'pages/oobe.vue'
    ]) {
      expect(readFileSync(resolve(ROOT, page), 'utf-8'), `${page} 缺 noindex 闸门`)
        .toContain('useNoindexPage()')
    }
  })

  it('canonical 全站单源：首页与列表页不得再手写第二份', () => {
    for (const page of ['pages/index.vue', 'pages/posts/index.vue']) {
      const src = readFileSync(resolve(ROOT, page), 'utf-8')
      // 请求 Host 派生的 origin 会被 swr 缓存固化成所有访客看到的规范地址
      expect(src, `${page} 仍在用 useRequestURL 拼 SEO 地址`).not.toContain('useRequestURL')
      expect(src, `${page} 自己发了一条 canonical`).not.toContain(`rel: 'canonical'`)
    }
  })
})
