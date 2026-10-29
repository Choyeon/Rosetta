/**
 * GEO 投递面契约（SEO_OPTIMIZATION.md §P2-3）。
 *
 * 这两个文件是纯文本投递面的 Nitro server route，跑不起来（要 Nuxt 运行时与后端），
 * 所以这里做的是源码级断言 + 真实页面路径存在性核对，钉住三条会静默失效的口径：
 *   1. 站点根只能来自配置（拒绝 Host 推导 —— 与 useSeo/robots 同一个红线，
 *      这些文件都带 s-maxage，一次 Host 伪造会被缓存给所有访客）；
 *   2. 后端连接走 resolveBackendEndpoint 单源，不许写死 127.0.0.1:8000；
 *   3. llms.txt 列出的每个核心页面必须在 pages/ 下真的有对应路由，
 *      否则这份"给 AI 的索引"会长期指向 404，比不列更糟。
 */

import { readFileSync, existsSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, it, expect } from 'vitest'

const FRONTEND_ROOT = resolve(__dirname, '../..')
const llmsRoute = readFileSync(join(FRONTEND_ROOT, 'server/routes/llms.txt.get.ts'), 'utf8')
/** RFC 9116 规定的位置；nitropack scanDir 的 globby 带 dot:true，点目录会被收录。 */
const SECURITY_ROUTE = 'server/routes/.well-known/security.txt.get.ts'
const securityRoute = readFileSync(join(FRONTEND_ROOT, SECURITY_ROUTE), 'utf8')

/** 从 llms.txt 源码里抠出 CORE_PAGES 的第二个元素（站内路径）。 */
function corePagePaths(source: string): string[] {
  const block = source.match(/const CORE_PAGES = \[([\s\S]*?)\] as const/)?.[1] ?? ''
  return [...block.matchAll(/\[\s*'[^']*'\s*,\s*'([^']+)'\s*\]/g)].map(m => m[1] ?? '')
}

describe('llms.txt 路由', () => {
  it('站点根取配置单源，后端连接走 resolveBackendEndpoint', () => {
    expect(llmsRoute).toContain('resolvePublicSiteOrigin(')
    expect(llmsRoute).toContain('resolveBackendEndpoint(')
    expect(llmsRoute).not.toMatch(/127\.0\.0\.1:8000/)
    expect(llmsRoute).not.toMatch(/x-forwarded-host/i)
    expect(llmsRoute).not.toMatch(/event\.node\.req\.headers\.host/i)
  })

  it('以 text/plain + 公开缓存头出口（AI 抓取器不解析 HTML 壳）', () => {
    expect(llmsRoute).toMatch(/content-type', 'text\/plain; charset=utf-8/)
    expect(llmsRoute).toMatch(/s-maxage=3600/)
  })

  it('文章清单来自 /blog/posts 的默认语言列表，与 /posts 同一份数据源', () => {
    expect(llmsRoute).toContain('/blog/posts')
    expect(llmsRoute).toMatch(/lang: 'zh'/)
    expect(llmsRoute).toContain('page_size: POSTS_LIMIT')
    expect(llmsRoute).toMatch(/const POSTS_LIMIT = 10\b/)
  })

  it('站点名与描述取 /settings/public 的 basic 组', () => {
    expect(llmsRoute).toContain('/settings/public')
  })

  it('两个上游各自独立 try/catch 降级，不抛 createError（后端不可达也要 200 文本）', () => {
    expect(llmsRoute).not.toContain('createError')
    expect(llmsRoute.match(/catch \(/g)?.length).toBeGreaterThanOrEqual(2)
  })

  it('四语首页来自 lib 单源清单（语言前缀不得在路由里再写一份）', () => {
    expect(llmsRoute).toContain('LOCALE_PATH_PREFIX_VARIANTS')
    expect(llmsRoute).not.toMatch(/en\|ja\|zh_Hant/)
  })

  it('核心页面清单里的每个路径都有真实路由（文件页或目录 index）', () => {
    const paths = corePagePaths(llmsRoute).filter(p => !p.endsWith('.xml'))
    expect(paths.length).toBeGreaterThanOrEqual(5)
    for (const path of paths) {
      const bare = path.replace(/^\//, '')
      const asFile = join(FRONTEND_ROOT, 'pages', `${bare}.vue`)
      const asIndex = join(FRONTEND_ROOT, 'pages', bare, 'index.vue')
      // '/' 是 pages/index.vue
      expect(existsSync(asFile) || existsSync(asIndex), `llms.txt 指向了不存在的页面：${path}`).toBe(true)
    }
  })
})

describe('/feed 兼容路由', () => {
  const feedRoute = readFileSync(join(FRONTEND_ROOT, 'server/routes/feed.get.ts'), 'utf8')
  const pageviewMiddleware = readFileSync(
    join(FRONTEND_ROOT, 'server/middleware/09-pageview-report.ts'),
    'utf8'
  )

  it('301 到唯一的真源 /rss.xml，而不是第二个 feed 生成器', () => {
    expect(feedRoute).toMatch(/sendRedirect\(\s*event,\s*'\/rss\.xml'\s*,\s*301\s*\)/)
    // 第二份正文迟早与 /rss.xml 分叉（features.enable_rss 只在那条链上生效）
    expect(feedRoute).not.toContain('proxyUpstreamText')
    expect(feedRoute).not.toContain('<rss')
    expect(feedRoute).not.toMatch(/127\.0\.0\.1:8000/)
  })

  it('与页面浏览上报的机器面清单同口径（清单认为 /feed 不是文档请求）', () => {
    expect(pageviewMiddleware).toMatch(/^\s*'\/feed',$/m)
  })
})

describe('security.txt 路由', () => {
  it('正文含 RFC 9116 必需的 Contact / Expires / Preferred-Languages / Canonical，且不公开任何邮箱地址', () => {
    expect(securityRoute).toContain('Contact:')
    expect(securityRoute).toContain('Expires:')
    expect(securityRoute).toContain('Preferred-Languages:')
    expect(securityRoute).toContain('Canonical:')
    expect(securityRoute).toContain('text/plain')
    // 形如 user@domain.tld 的硬编码邮箱一律不允许；设置里也没有"收安全报告"的收件箱键
    expect(securityRoute).not.toMatch(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/)
  })

  it('Contact 指向真实存在的站内沟通入口页', () => {
    for (const path of ['/about', '/guestbook']) {
      expect(existsSync(join(FRONTEND_ROOT, 'pages', `${path.replace(/^\//, '')}.vue`)),
        `security.txt 的 Contact 指向了不存在的页面：${path}`).toBe(true)
    }
  })

  it('Expires 是生成时算出的未来时间，不是写死的历史日期', () => {
    expect(securityRoute).toContain('Date.now()')
    expect(securityRoute).toMatch(/toISOString\(\)/)
  })

  it('站点根与缓存头沿用同一口径（配置单源 + 与 robots 同档的 s-maxage）', () => {
    expect(securityRoute).toContain('resolvePublicSiteOrigin(')
    expect(securityRoute).toContain('public, max-age=0, s-maxage=3600, stale-while-revalidate=86400')
    expect(securityRoute).not.toMatch(/127\.0\.0\.1:8000|event\.node\.req\.headers\.host/i)
  })

  it('全仓只有一条 security.txt 生成器（别名中间件与重复正文文件都已退役）', () => {
    expect(existsSync(join(FRONTEND_ROOT, SECURITY_ROUTE))).toBe(true)
    expect(existsSync(join(FRONTEND_ROOT, 'server/routes/security.txt.get.ts'))).toBe(false)
    expect(existsSync(join(FRONTEND_ROOT, 'server/middleware/well-known-security-alias.ts'))).toBe(false)
    expect(existsSync(join(FRONTEND_ROOT, 'server/routes/llms.txt.get.ts'))).toBe(true)
  })
})
