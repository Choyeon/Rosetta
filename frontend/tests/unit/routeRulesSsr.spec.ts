/**
 * SPA 精准反选契约（AGENTS.md §2.2）：锁定「哪些路由是 ssr:false、哪些必须保留 SSR」。
 *
 * 为什么用文本解析而不是 import nuxt.config：defineNuxtConfig 是 Nuxt 注入的全局，
 * 在 vitest 里 import 会连带拉起整个构建链。routeRules 的渲染开关是纯字面量，
 * 按行取 `'<path>': { ... }` 足够精确，且断言的是配置真值而非记忆。
 *
 * /oobe 是本契约里最容易被"顺手统一"改坏的一条：它刻意保留 SSR，
 * 撤销 ssr:false 是为了让安装完成后的 SSR 级 302 不与客户端 navigateTo 抢跑成白屏。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// happy-dom 下 import.meta.url 是 http URL，fileURLToPath 会直接抛错；
// vitest 的 root 就是 frontend/，按 cwd 解析最稳。
const configSource = readFileSync(resolve(process.cwd(), 'nuxt.config.ts'), 'utf8')

interface RouteRule {
  ssr?: boolean
  swr?: number | boolean
  cache?: string
}

function parseRouteRules(source: string): Map<string, RouteRule> {
  const start = source.indexOf('routeRules:')
  expect(start, 'nuxt.config.ts 必须存在 routeRules 段').toBeGreaterThan(-1)
  const rules = new Map<string, RouteRule>()
  // routeRules 之后的每个单行字面量条目（多行的 rss/sitemap 段不属于渲染反选契约）。
  for (const line of source.slice(start).split('\n')) {
    const match = /^\s*'([^']+)':\s*\{(.*)\}\s*,?\s*$/.exec(line)
    if (!match) continue
    const [, path, body] = match
    const rule: RouteRule = {}
    if (/ssr:\s*false/.test(body!)) rule.ssr = false
    if (/ssr:\s*true/.test(body!)) rule.ssr = true
    const swr = /swr:\s*(false|true|\d+)/.exec(body!)
    if (swr) rule.swr = swr[1] === 'false' ? false : swr[1] === 'true' ? true : Number(swr[1])
    const cache = /'Cache-Control':\s*'([^']+)'/.exec(body!)
    if (cache) rule.cache = cache[1]
    rules.set(path!, rule)
  }
  return rules
}

const rules = parseRouteRules(configSource)

const nitroSource = readFileSync(
  resolve(process.cwd(), 'server/plugins/spa-serverrendered-zero.nitro.ts'),
  'utf8'
)

describe('nuxt.config routeRules · SSR 反选契约', () => {
  /**
   * 跨文件隐性耦合守卫：Nitro 插件 spa-serverrendered-zero 会把白名单前缀路径的
   * payload.serverRendered 改成 false。它只在「路由确实配了 ssr:false」时才正确；
   * 一旦某个前缀没有对应的 routeRules（Nuxt 里最常见的坑是只写 '/x/**' 而实际路由
   * 是 '/x' —— `path/**` 不匹配 path 本身），就会出现：
   *   服务端真的 SSR 出了 HTML  →  插件说没渲染  →  客户端丢掉 SSR DOM 重新 CSR
   * 表现为导航过去先白屏一帧，且不报任何错。这条断言把两处口径钉在一起。
   */
  it('Nitro SPA 白名单的每个前缀都必须在 routeRules 里有 ssr:false 覆盖', () => {
    const block = /const SPA_PREFIXES[^=]*=\s*\[([\s\S]*?)]\s*as const/.exec(nitroSource)
    expect(block, '未解析到 SPA_PREFIXES').not.toBeNull()
    const prefixes = [...block![1]!.matchAll(/'([^']+)'/g)].map(m => m[1]!)
    expect(prefixes.length).toBeGreaterThan(0)

    const missing: string[] = []
    for (const prefix of prefixes) {
      const covered = [...rules.entries()].some(
        ([path, rule]) =>
          rule.ssr === false
          && (path === prefix || path === `${prefix}/**` || path.startsWith(`${prefix}/`))
      )
      if (!covered) missing.push(prefix)
    }
    expect(
      missing,
      `以下前缀被 Nitro 当成 SPA，却没有 ssr:false 的 routeRules：${missing.join(', ')}`
    ).toEqual([])
  })

  it('ssr:false 的路由集合与 AGENTS.md §2.2 一致，不增不减', () => {
    const spaOnly = [...rules.entries()]
      .filter(([, rule]) => rule.ssr === false)
      .map(([path]) => path)
      .sort()
    expect(spaOnly).toEqual([
      '/@fs/**',
      '/@id/**',
      '/@vite/**',
      '/account',
      '/account/**',
      '/admin',
      '/admin/**',
      '/admin/docs/**',
      '/forgot-password',
      '/login',
      '/register',
      // '/search' 与 '/search/**' 必须成对存在：Nuxt 的 `path/**` 不匹配 path 自身，
      // 只写后者会让 /search 落回 SSR，而 Nitro 的 spa-serverrendered-zero 插件
      // 白名单又含 '/search' → SSR 内容被判定为未渲染而丢弃，导航过去白闪一帧。
      '/search',
      '/search/**'
    ])
  })

  it('/oobe 保留 SSR（只禁缓存）——撤销 ssr:false 的历史修复不得回退', () => {
    const oobe = rules.get('/oobe')
    expect(oobe, 'routeRules 必须显式声明 /oobe').toBeDefined()
    expect(oobe!.ssr, '/oobe 不允许再写 ssr:false').not.toBe(false)
    expect(oobe!.swr).toBe(false)
    expect(oobe!.cache).toContain('no-store')
  })

  it('反选为 SPA 的路由一律禁缓存，公开内容页一律带 s-maxage', () => {
    for (const [path, rule] of rules.entries()) {
      if (rule.ssr === false || path === '/oobe') {
        expect(rule.cache, `${path} 必须 no-store`).toContain('no-store')
      }
    }
    for (const path of ['/', '/posts', '/post/**', '/categories/**', '/tags/**', '/authors/**', '/page/**']) {
      const rule = rules.get(path)
      expect(rule, `公开页 ${path} 必须有 routeRules`).toBeDefined()
      expect(rule!.ssr, `公开页 ${path} 不得反选 SSR`).not.toBe(false)
      expect(rule!.cache, `公开页 ${path} 必须共享缓存`).toMatch(/s-maxage=\d+/)
    }
  })
})
