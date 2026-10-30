/**
 * 捐助页 `/sponsor` 的「可索引性」两侧同口径守卫。
 *
 * 这一页是否可索引由 donate 分组决定（`enable` 关闭或 `methods` 为空 ⇒ `noindex`）：
 *  - 前端 `pages/sponsor.vue::sponsorEmpty` 决定 `<meta name="robots">`；
 *  - 后端 `_sponsor_page_indexable`（`backend/api/blog.py`）决定它是否进 `sitemap-pages.xml`。
 *
 * 两处判据漂移的表现都是静默的：前端可索引而后端漏提交 → 这一页只剩内链这一个
 * 发现入口；前端 noindex 而后端照交 → 向爬虫提交一个自我声明"别收录"的地址。
 * 所以这里同时钉住两侧的表达式，并断言 sitemap 调用点真的把它传下去了。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const sponsorPage = readFileSync(resolve(ROOT, 'pages/sponsor.vue'), 'utf8')
const backendBlog = readFileSync(resolve(ROOT, '../backend/api/blog.py'), 'utf8')

describe('/sponsor 与 sitemap-pages.xml 同口径', () => {
  it('前端空壳判据仍是 enable ∧ methods 两条（改判据要同批改后端）', () => {
    expect(sponsorPage).toContain(
      'const sponsorEmpty = computed(() => !donate.value.enable || donate.value.methods.length === 0)'
    )
    expect(sponsorPage).toContain('noindex: sponsorEmpty')
  })

  it('后端判据与前端同形：未保存分组时默认 enable=true，methods 必须非空', () => {
    expect(backendBlog).toContain('async def _sponsor_page_indexable(db)')
    expect(backendBlog).toContain('donate = await read_group("donate", db)')
    expect(backendBlog).toContain('bool_of(donate, "enable", True)')
    expect(backendBlog).toContain('isinstance(methods, list) and bool(methods)')
  })

  it('sitemap 只在 include_sponsor 为真时补 /sponsor，且调用点按分组状态传值', () => {
    expect(backendBlog).toContain('include_sponsor: bool = False')
    expect(backendBlog).toContain('if include_sponsor:')
    expect(backendBlog).toContain('f"{site_url}/sponsor"')
    expect(backendBlog).toContain('rel_path="/sponsor"')
    expect(backendBlog).toContain('include_sponsor=await _sponsor_page_indexable(db)')
    // /sponsor 不能进"恒存在且恒可索引"的固定路由表，否则 noindex 页也会被提交
    const staticBlock = /_STATIC_SITEMAP_ROUTES[^=]*= \[([\s\S]*?)\n\]/.exec(backendBlog)?.[1] ?? ''
    expect(staticBlock).not.toContain('"/sponsor"')
  })
})
