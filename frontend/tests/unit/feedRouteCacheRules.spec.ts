/**
 * 投递面 server-routes 的缓存契约：每条 feed 路由都必须在 routeRules 里显式登记，
 * 且登记的 `Cache-Control` 与 handler 自己写的那个字面量**逐字相等**。
 *
 * 为什么不能靠 `'/**': { swr: 600 }` 兜：Nitro 的 routeRules 是按「路由处理器」套缓存的，
 * 通配规则同样会包住 server/routes 下的静态路由。2026-10-30 线上实测：后端子 sitemap
 * 已含新增的 `/authors`，Nitro 仍在发 600s 前的旧正文，且 handler 的
 * `public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400` 被 swr 处理器
 * 改写成裸 `s-maxage=600, stale-while-revalidate`。新增一个 feed 路由而不登记 = 静默旧内容，
 * 所以这里按目录反扫：handler 文件集合 ⇔ routeRules 键集合，两边对不上就红。
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

/** 取 routeRules 里某条目的完整块（条目必须独占多行书写，见 nuxt.config 注释口径） */
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

  for (const route of routes) {
    it(`${route.path} 的 Cache-Control 与 handler 一致，且 swr 窗口 = s-maxage`, () => {
      const handler = readFileSync(route.file, 'utf8')
      const expected = handlerHeader(handler, 'cache-control')
      expect(expected, `${route.path} handler 必须显式写 Cache-Control`).toBeTruthy()

      const block = ruleBlock(route.path)
      expect(
        block,
        `${route.path} 必须在 routeRules 显式登记（否则落进 '/**' 的 swr 600，静默 10 分钟旧内容）`
      ).not.toBeNull()

      const declared = /'Cache-Control':\s*'([^']+)'/.exec(block!)
      expect(declared?.[1], `${route.path} routeRules 缺 Cache-Control`).toBe(expected)

      const swr = /swr:\s*(\d+)/.exec(block!)
      const smaxage = /s-maxage=(\d+)/.exec(expected!)?.[1]
      expect(swr?.[1], `${route.path} routeRules 缺 swr`).toBe(smaxage)
    })

    it(`${route.path} 的 Content-Type 与 handler 一致`, () => {
      const handler = readFileSync(route.file, 'utf8')
      const expected = handlerHeader(handler, 'content-type')
      // proxyUpstreamText 的缺省值就是 sitemap 三兄弟的口径
      const resolved = expected ?? 'application/xml; charset=utf-8'
      const block = ruleBlock(route.path)
      const declared = /'Content-Type':\s*'([^']+)'/.exec(block!)
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
