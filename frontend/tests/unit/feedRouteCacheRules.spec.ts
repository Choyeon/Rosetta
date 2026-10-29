/**
 * 投递面 server-routes 的缓存契约：每条 feed 路由都必须在 routeRules 里显式登记，
 * 且登记的两个数（swr / cache.staleMaxAge）必须与 handler 自己写的 Cache-Control 同口径。
 *
 * 为什么不能靠 `'/**': { swr: 600 }` 兜：Nitro 的 routeRules 是按「路由处理器」套缓存的，
 * 通配规则同样会包住 server/routes 下的静态路由。2026-10-30 线上实测：后端子 sitemap
 * 已含新增的 `/authors`，Nitro 仍在发 600s 前的旧正文。
 *
 * 为什么 routeRules 里不写 'Cache-Control'：swr 缓存处理器写回响应时会用
 * `s-maxage=<maxAge>[, stale-while-revalidate=<staleMaxAge>]` 整条覆写 handler 设的头
 * （nitropack/dist/runtime/internal/cache.mjs），写在 headers 里的完整串线上不落地 ——
 * 留着它等于又造一份"文档承诺、运行时不算数"的配置。生效口径就是 swr 与 staleMaxAge。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const cwd = process.cwd()
const configSource = readFileSync(resolve(cwd, 'nuxt.config.ts'), 'utf8')
const routesDir = resolve(cwd, 'server/routes')

/** `server/routes` 下的 `.get.ts` → Nitro 路由路径（点目录保留，如 `.well-known`） */
function feedRoutes(): { path: string, file: string }[] {
  const out: { path: string, file: string }[] = []
  const walk = (dir: string, prefix: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const abs = resolve(dir, entry.name)
      if (entry.isDirectory()) {
        walk(abs, `${prefix}/${entry.name}`)
        continue
      }
      if (!entry.name.endsWith('.get.ts')) continue
      out.push({ path: `${prefix}/${entry.name.slice(0, -'.get.ts'.length)}`, file: abs })
    }
  }
  walk(routesDir, '')
  return out
}

/** 取 routeRules 里某条目的完整块（条目必须独占多行书写） */
function ruleBlock(path: string): string | null {
  const marker = `\n    '${path}': {`
  const start = configSource.indexOf(marker)
  if (start < 0) return null
  const end = configSource.indexOf('\n    }', start + marker.length)
  return end < 0 ? null : configSource.slice(start, end)
}

/** handler 声明的响应头：proxy 口写 `cacheControl:`，自组装口写 `setHeader(event, …)` */
function handlerHeader(source: string, name: string): string | null {
  const key = name.toLowerCase() === 'cache-control' ? 'cacheControl' : 'contentType'
  const field = new RegExp(`${key}:\\s*'([^']+)'`).exec(source)
  if (field) return field[1]!
  const setter = new RegExp(
    `setHeader\\(\\s*event,\\s*'${name.toLowerCase()}'\\s*,\\s*'([^']+)'\\s*\\)`
  ).exec(source)
  return setter ? setter[1]! : null
}

const routes = feedRoutes()
/** 纯跳转别名不承载正文：swr / staleMaxAge / Content-Type 三条契约对它都不适用。 */
const isRedirectAlias = (file: string) => /sendRedirect\(/.test(readFileSync(file, 'utf8'))
const feedBodies = routes.filter(r => !isRedirectAlias(r.file))
const redirectAliases = routes.filter(r => isRedirectAlias(r.file))
const EXPECTED_STALE = '86400'

describe('feed server-routes ⇔ routeRules 显式登记', () => {
  it('能扫到投递面路由（目录口径变化时先修这里，不要删断言）', () => {
    const paths = routes.map(r => r.path)
    for (const expected of [
      '/rss.xml',
      '/sitemap.xml',
      '/sitemap-pages.xml',
      '/sitemap-posts.xml',
      '/sitemap-taxonomies.xml',
      '/robots.txt',
      '/llms.txt',
      '/.well-known/security.txt'
    ]) {
      expect(paths, `缺少 ${expected}`).toContain(expected)
    }
  })

  it('跳转别名清单固定为 /feed（301 → /rss.xml，不产出正文）', () => {
    expect(redirectAliases.map(r => r.path)).toEqual(['/feed'])
  })

  for (const route of feedBodies) {
    it(`${route.path} 的 swr 与 handler 的 s-maxage 同口径`, () => {
      const handler = readFileSync(route.file, 'utf8')
      const expected = handlerHeader(handler, 'cache-control')
      expect(expected, `${route.path} handler 必须显式写 Cache-Control`).toBeTruthy()

      const block = ruleBlock(route.path)
      expect(
        block,
        `${route.path} 必须在 routeRules 显式登记（否则落进 '/**' 的 swr 600，静默 10 分钟旧内容）`
      ).not.toBeNull()

      const smaxage = /s-maxage=(\d+)/.exec(expected!)?.[1]
      const swr = /swr:\s*(\d+)/.exec(block!)
      expect(swr?.[1], `${route.path} routeRules 的 swr 应等于 handler 的 s-maxage`).toBe(smaxage)
    })

    it(`${route.path} 的 staleMaxAge 与 handler 的 stale-while-revalidate 同口径`, () => {
      const handler = readFileSync(route.file, 'utf8')
      const stale = /stale-while-revalidate=(\d+)/.exec(handlerHeader(handler, 'cache-control')!)
      const block = ruleBlock(route.path)!
      const declared = /staleMaxAge:\s*(\d+)/.exec(block)
      if (stale) {
        expect(declared?.[1], `${route.path} 缺 cache.staleMaxAge（swr 处理器会退化成裸 stale-while-revalidate）`)
          .toBe(stale[1])
        expect(stale[1], `${route.path} 的软过期窗口应为 ${EXPECTED_STALE}s`).toBe(EXPECTED_STALE)
      } else {
        expect(declared, `${route.path} handler 没声明软过期窗口，routeRules 也不该声明`).toBeNull()
      }
    })

    it(`${route.path} 的 routeRules 不写无效的 Cache-Control`, () => {
      const block = ruleBlock(route.path)!
      expect(
        /'Cache-Control'/.test(block),
        `${route.path}: swr 处理器会整条覆写 Cache-Control，写在 routeRules.headers 里不会落地`
      ).toBe(false)
    })

    it(`${route.path} 的 Content-Type 与 handler 一致`, () => {
      const handler = readFileSync(route.file, 'utf8')
      const expected = handlerHeader(handler, 'content-type')
      // proxyUpstreamText 的缺省值就是 sitemap 三兄弟的口径
      const resolved = expected ?? 'application/xml; charset=utf-8'
      const declared = /'Content-Type':\s*'([^']+)'/.exec(ruleBlock(route.path)!)
      expect(declared?.[1], `${route.path} routeRules 的 Content-Type 应与 handler 一致`).toBe(
        resolved
      )
    })
  }

  it('投递面不进语言前缀镜像（/en/llms.txt 这类键不得手写）', () => {
    for (const route of routes) {
      for (const prefix of ['/en', '/ja', '/zh_Hant']) {
        expect(configSource).not.toContain(`'${prefix}${route.path}'`)
      }
    }
  })
})
