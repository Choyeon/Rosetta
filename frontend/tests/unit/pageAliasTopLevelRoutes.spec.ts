/**
 * `/page/<slug>` 兼容口的「哪些 slug 要跳走」清单 ⇔ 顶级真实路由。
 *
 * 为什么需要守卫：`/page/about` 这类 URL 有三处口径在管——
 *  - `server/middleware/06-page-alias.ts`：命中清单就 SSR 层 301（爬虫与首屏看到的是真 301）；
 *  - `pages/page/[slug].vue::KNOWN_TOP_LEVEL`：客户端兜底（中间件被绕过时）；
 *  - 后端 `_TOP_LEVEL_ROUTE_SLUGS`（`backend/api/blog.py`）：sitemap 用它判定
 *    "这条独立页记录没有可提交的规范地址"并整条跳过。
 * 三者共用前端 `lib/top-level-routes.ts` 那份清单；与后端拆分点漂移或清单漏项的表现
 * 都是静默的：后端多一条 → 库里那条正文从 sitemap 消失；前端少一条 → `/page/<slug>`
 * 200 渲染出库里的另一份正文，与其 canonical（指向内建页）内容不一致。
 *
 * 另外三条：
 *  - 清单里每个 slug 必须有真实顶级路由（`pages/<slug>.vue` 或 `pages/<slug>/index.vue`），
 *    否则那条 301 会把旧链接送到 404 —— 比不跳更糟；
 *  - `page` 只能出现在后端清单里：它是本兼容口的根，前端跳 `/page/page` → `/page`
 *    等于原地打转；
 *  - 中间件必须就地写 `no-store`：它用 `sendRedirect` 直接结束响应、不走渲染器，
 *    routeRules 的 `public, max-age=0, s-maxage=…` 会原样留在 301 上（仓库口径：3xx 一律 no-store）。
 */
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const sharedList = readFileSync(resolve(ROOT, 'lib/top-level-routes.ts'), 'utf8')
const aliasPage = readFileSync(resolve(ROOT, 'pages/page/[slug].vue'), 'utf8')
const middleware = readFileSync(resolve(ROOT, 'server/middleware/06-page-alias.ts'), 'utf8')
const backendBlog = readFileSync(resolve(ROOT, '../backend/api/blog.py'), 'utf8')

/** 前端单源清单：`TOP_LEVEL_ROUTE_SLUGS: readonly string[] = [ 'a', 'b', … ]`。 */
function frontendSlugs(): string[] {
  const block
    = /TOP_LEVEL_ROUTE_SLUGS: readonly string\[\] = \[([\s\S]*?)\]/.exec(sharedList)?.[1] ?? ''
  return [...block.matchAll(/'([^']+)'/g)].map(m => m[1]!).sort()
}

/** 后端：`_TOP_LEVEL_ROUTE_SLUGS = frozenset({ … })` 里的字符串。 */
function backendSlugs(): string[] {
  const block = /_TOP_LEVEL_ROUTE_SLUGS = frozenset\(([\s\S]*?)\n\)/.exec(backendBlog)?.[1] ?? ''
  return [...block.matchAll(/"([^"]+)"/g)].map(m => m[1]!).sort()
}

describe('/page/<slug> 兼容口', () => {
  it('清单能解析出来（写法变化时先修这里，不要删断言）', () => {
    expect(frontendSlugs().length).toBeGreaterThanOrEqual(15)
    expect(backendSlugs().length).toBeGreaterThanOrEqual(frontendSlugs().length)
  })

  it('前端与后端清单逐条一致，只允许后端多一个 page', () => {
    const backendOnly = backendSlugs().filter(s => s !== 'page')
    expect(frontendSlugs()).toEqual(backendOnly)
  })

  it('每个 slug 都有真实顶级路由（301 不许落到 404）', () => {
    for (const slug of frontendSlugs()) {
      const asFile = resolve(ROOT, 'pages', `${slug}.vue`)
      const asIndex = resolve(ROOT, 'pages', slug, 'index.vue')
      expect(
        existsSync(asFile) || existsSync(asIndex),
        `/page/${slug} 会 301 到 /${slug}，但 pages/ 下没有这个顶级路由`
      ).toBe(true)
    }
  })

  it('清单里不出现兼容口自己（page）与首页（index）', () => {
    const slugs = frontendSlugs()
    expect(slugs).not.toContain('page')
    expect(slugs).not.toContain('index')
  })

  it('页面与中间件都读同一份清单，页面不得再抄一份', () => {
    expect(aliasPage).toContain('import { TOP_LEVEL_ROUTE_SLUGS } from \'~~/lib/top-level-routes\'')
    expect(aliasPage).not.toMatch(/const KNOWN_TOP_LEVEL: readonly string\[\] = \[\s*'/)
    expect(middleware).toContain('from \'../../lib/top-level-routes\'')
  })

  it('中间件先剥语言前缀、只认单段 slug，并给 301 就地写 no-store', () => {
    expect(middleware).toContain('stripLocalePathPrefix(')
    expect(middleware).toContain('/^\\/page\\/([^/]+)$/')
    expect(middleware).toContain('setHeader(event, \'cache-control\', \'no-store\')')
    expect(middleware).toContain('sendRedirect(event, `${prefix}/${slug}${search}`, 301)')
  })
})
