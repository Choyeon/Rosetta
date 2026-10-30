/**
 * 空目录页（/categories · /tags · /series · /gallery）的「可索引性」两侧同口径守卫。
 *
 * 这四个页面是用户内容的集合落地页：集合为空时只有一句"暂无…"占位，因此
 *  - 前端输出 `<meta name="robots" content="noindex, follow">`；
 *  - 后端 sitemap 同步跳过（分类学 sitemap 的三个目录根 + pages sitemap 的 /gallery）。
 *
 * 两侧漂移都是静默的：前端 noindex 而后端照交 → 向爬虫提交一个自我声明"别收录"的
 * 地址；后端跳过而前端可索引 → 可索引页失去 sitemap 这个唯一发现入口（这些页在
 * 站内导航里的位置并不稳定）。所以这里把两侧表达式、判据的"可空性保护"和传入点一起钉住。
 *
 * 另外两条硬约束：
 *  - noindex 只能建立在「确实取到空列表」上（`!pending && !error && empty`）：
 *    加载中或请求失败也判 noindex 的话，一次网络故障会把有内容的目录页摘出索引，
 *    而这两类页面的 swr 会把判错的结果缓存 10–60 分钟；
 *  - 目录根不能进 `_STATIC_SITEMAP_ROUTES`（那张表是"恒存在且恒可索引"），
 *    否则"条件性提交"会被无条件那一份盖回来，同一 URL 还会在 sitemap 索引里出现两次。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const categoriesPage = readFileSync(resolve(ROOT, 'pages/categories/index.vue'), 'utf8')
const tagsPage = readFileSync(resolve(ROOT, 'pages/tags/index.vue'), 'utf8')
const seriesPage = readFileSync(resolve(ROOT, 'pages/series/index.vue'), 'utf8')
const galleryPage = readFileSync(resolve(ROOT, 'pages/gallery.vue'), 'utf8')
const backendBlog = readFileSync(resolve(ROOT, '../backend/api/blog.py'), 'utf8')

/** `generate_taxonomy_sitemap` 函数体（到下一个顶层 `def` 之前）。 */
function taxonomyBody(): string {
  const start = backendBlog.indexOf('def generate_taxonomy_sitemap(')
  expect(start).toBeGreaterThan(-1)
  const rest = backendBlog.slice(start)
  const end = rest.indexOf('\ndef ')
  return end > 0 ? rest.slice(0, end) : rest
}

describe('空目录页与 sitemap 同口径', () => {
  it('四个页面的 noindex 判据都带「加载中 / 出错」保护', () => {
    const cases: Array<[string, string, string]> = [
      [categoriesPage, 'categoriesEmpty', '!_catsLoading.value && !catsLoadError.value && categories.value.length === 0'],
      [tagsPage, 'tagsEmpty', '!_tagsLoading.value && !tagsLoadError.value && tags.value.length === 0'],
      [seriesPage, 'seriesEmpty', '!pending.value && !loadError.value && seriesList.value.length === 0'],
      // 相册用接口给的 total（已发布相册数）：本地数组只装当前页，翻到空页不等于目录为空
      [galleryPage, 'galleryEmpty', '!pending.value && !albumsError.value && totalAlbums.value === 0']
    ]
    for (const [source, name, expression] of cases) {
      expect(source).toContain(`const ${name} = computed(`)
      expect(source).toContain(expression)
      expect(source).toContain(`noindex: ${name}`)
    }
  })

  it('分类学 sitemap 的三个目录根只在集合非空时输出', () => {
    const body = taxonomyBody()
    expect(body).toMatch(/if categories:[\s\S]{0,400}?f"\{site_url\}\/categories"/)
    expect(body).toMatch(/if tags:[\s\S]{0,400}?f"\{site_url\}\/tags"/)
    expect(body).toMatch(/if series:[\s\S]{0,400}?f"\{site_url\}\/series"/)
  })

  it('/gallery 由 include_gallery 条件提交，且判据只数已上架相册', () => {
    expect(backendBlog).toContain('async def _gallery_directory_indexable(db)')
    expect(backendBlog).toContain('Album.is_published.is_(True)')
    expect(backendBlog).toContain('include_gallery: bool = False')
    expect(backendBlog).toContain('if include_gallery:')
    expect(backendBlog).toContain('f"{site_url}/gallery"')
    expect(backendBlog).toContain('rel_path="/gallery"')
    expect(backendBlog).toContain('include_gallery=await _gallery_directory_indexable(db)')
  })

  it('目录根不留在「恒存在且恒可索引」的固定路由表里', () => {
    const staticBlock = /_STATIC_SITEMAP_ROUTES[^=]*= \[([\s\S]*?)\n\]/.exec(backendBlog)?.[1] ?? ''
    for (const path of ['"/gallery"', '"/categories"', '"/tags"', '"/series"']) {
      expect(staticBlock).not.toContain(path)
    }
  })
})
