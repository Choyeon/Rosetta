/**
 * `/page/<slug>` 兼容口的「哪些 slug 要跳走」清单 ⇔ 顶级真实路由。
 *
 * 为什么需要守卫：`/page/about` 这类 URL 有两份真源在管——
 *  - 前端 `pages/page/[slug].vue::KNOWN_TOP_LEVEL`：命中就在浏览器里 301 到内建页；
 *  - 后端 `_TOP_LEVEL_ROUTE_SLUGS`（`backend/api/blog.py`）：sitemap 用它判定
 *    "这条独立页记录没有可提交的规范地址"并整条跳过。
 * 两份清单漂移的表现都是静默的：后端多一条 → 库里那条正文从 sitemap 消失；
 * 前端少一条 → `/page/<slug>` 渲染出库里的另一份正文，与其 canonical（指向内建页）
 * 内容不一致，成为一份 200 的重复页。
 *
 * 另外两条：
 *  - 清单里每个 slug 必须有真实顶级路由（`pages/<slug>.vue` 或 `pages/<slug>/index.vue`），
 *    否则那条 301 会把旧链接送到 404 —— 比不跳更糟；
 *  - `page` 只能出现在后端清单里：它是本兼容口的根，前端跳 `/page/page` → `/page`
 *    等于原地打转。
 */
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const aliasPage = readFileSync(resolve(ROOT, 'pages/page/[slug].vue'), 'utf8')
const backendBlog = readFileSync(resolve(ROOT, '../backend/api/blog.py'), 'utf8')

/** 前端：`const KNOWN_TOP_LEVEL: string[] = [ 'a', 'b', … ]` 里的字符串。 */
function frontendSlugs(): string[] {
  const block = /const KNOWN_TOP_LEVEL: string\[\] = \[([\s\S]*?)\]/.exec(aliasPage)?.[1] ?? ''
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
})
