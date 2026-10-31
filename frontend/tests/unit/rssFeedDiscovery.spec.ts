/**
 * 分类 / 标签归档页的「本范围订阅源」接线守卫（批次 #131）。
 *
 * 这一族此前的形状是**整段不存在**：`/rss.xml` 只有全站那一份，分类页与标签页既不产出
 * `<link rel="alternate">`，后端 `/blog/rss` 也没有按分类/标签裁剪的能力。补了后端参数而前端
 * 不产出链接，阅读器与浏览器扩展就发现不了「这个分类本身可订阅」；反过来前端挂了链接而后端
 * 忽略参数，等于给爬虫发一个「承诺只订这个分类、实际播全站文章」的假源。所以四个面必须同时对账：
 *
 * 1. `composables/useRssFeedLink.ts` 的三条「不得输出」闸门（slug 空 / 页面不存在态 / RSS 开关关掉）
 *    与 `rel` 字面量、href 参数名；`rel` 写成变量会让 unhead 挑不到 link 变体。
 * 2. 两个页面各自调用它，并把 `active` 绑到本页的 `*NotFound`——页面正在 noindex 时
 *    还 advertise 一个该分类的源，是给爬虫两份互相矛盾的信号。
 * 3. Nitro `/rss.xml` 透传 `category` / `tag`，且先过形状闸门（这两参数会进缓存键）。
 * 4. 后端 `get_rss_feed` 真的声明了同名查询参数；前端拼的键名与后端接受的键名必须逐字相等。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')

// 仓库混用 CRLF 与 LF：多行标记必须先归一，否则正则永远找不到
function readSource(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')
}

const composable = readSource('composables/useRssFeedLink.ts')
const categoryPage = readSource('pages/categories/[slug].vue')
const tagPage = readSource('pages/tags/[slug].vue')
const nitroRoute = readSource('server/routes/rss.xml.get.ts')
const backendBlog = readSource('../backend/api/blog.py')

/** 取 `async def get_rss_feed(...)`: 这一段签名，只在这一段里对账参数名。 */
function rssEndpointSignature(source: string): string {
  const start = source.indexOf('async def get_rss_feed(')
  expect(start, '后端 /blog/rss 端点函数必须存在').toBeGreaterThan(-1)
  const end = source.indexOf('):', start)
  expect(end, 'get_rss_feed 签名必须能闭合').toBeGreaterThan(start)
  return source.slice(start, end)
}

describe('useRssFeedLink 的三条不输出闸门与 link 形状', () => {
  it('slug 为空、页面处于不存在态、RSS 开关关掉时都不得产出 link', () => {
    expect(composable).toMatch(/if \(!slug\) return \{\}/)
    expect(composable).toMatch(/opts\.active !== undefined && !toValue\(opts\.active\)\) return \{\}/)
    expect(composable, '开关源必须是运行期的 site.features，不是构建期常量')
      .toMatch(/!site\.features\.value\?\.enable_rss\) return \{\}/)
  })

  it('rel 必须是字面量 alternate，href 带 lang 与 kind 两档参数', () => {
    expect(composable).toMatch(/rel: 'alternate'/)
    expect(composable).toMatch(/type: 'application\/rss\+xml'/)
    expect(composable, 'lang 必须带：RSS 是单语言源，不带就会让英文页的 feed 播中文标题')
      .toMatch(/href: `\/rss\.xml\?lang=\$\{encodeURIComponent\(locale\.value\)\}&\$\{opts\.kind\}=\$\{encodeURIComponent\(slug\)\}`/)
  })

  it('kind 只允许 category / tag 两档，避免拼出后端不认的参数名', () => {
    expect(composable).toMatch(/kind: 'category' \| 'tag'/)
  })
})

describe('分类页与标签页各自接线，并把 active 绑到本页的「不存在」判定', () => {
  for (const [label, source, kind, notFound] of [
    ['categories/[slug].vue', categoryPage, 'category', 'catNotFound'],
    ['tags/[slug].vue', tagPage, 'tag', 'tagNotFound']
  ] as const) {
    it(`${label} 以 kind=${kind} 调用，且 active 读 !${notFound}`, () => {
      const call = /useRssFeedLink\(\{[\s\S]*?\}\)/.exec(source)
      expect(call, `页面必须调用 useRssFeedLink（链接不是后端能裁就自动出现的）`).not.toBeNull()
      const body = call![0]
      expect(body).toContain(`kind: '${kind}'`)
      expect(body).toMatch(/\bslug,/, 'slug 用页面自己的响应式值，不要传字面量')
      expect(body).toMatch(/label: computed\(\(\) => \w+\.value\)/)
      expect(body).toContain(`active: computed(() => !${notFound}.value)`)
    })

    it(`${label} 不得再自己拼第二份 alternate link`, () => {
      expect(source, '同一页两条 alternate 会让阅读器自己挑一条，等于把范围又交回落')
        .not.toMatch(/rel: 'alternate'/)
    })
  }
})

describe('Nitro /rss.xml 透传两个分类学参数', () => {
  it('category / tag 都要转发给后端，且先过 slug 形状闸门', () => {
    expect(nitroRoute).toMatch(/feedSlug\(raw: unknown\)/)
    expect(nitroRoute).toMatch(/const categorySlug = feedSlug\(q\.category\)/)
    expect(nitroRoute).toMatch(/params\.set\('category', categorySlug\)/)
    expect(nitroRoute).toMatch(/const tagSlug = feedSlug\(q\.tag\)/)
    expect(nitroRoute).toMatch(/params\.set\('tag', tagSlug\)/)
  })

  it('闸门必须挡控制字符与标记符号（这两参数会进缓存键与响应正文）', () => {
    expect(nitroRoute).toMatch(/FEED_SLUG_BAD_CHARS\s*=\s*\/\[[\s\S]*?u0000-[\s\S]*?<>&/)
    expect(nitroRoute).toMatch(/FEED_SLUG_MAX_LEN/)
  })
})

describe('后端 /blog/rss 的签名接受同名参数', () => {
  const signature = rssEndpointSignature(backendBlog)

  it('category 与 tag 都是可选查询参数，键名与前端拼的一致', () => {
    expect(signature).toMatch(/\bcategory:\s*str\s*\|\s*None\s*=\s*Query\(/)
    expect(signature).toMatch(/\btag:\s*str\s*\|\s*None\s*=\s*Query\(/)
  })

  it('两参数都进 SQL 过滤，并一起进缓存键（进 WHERE 不进键＝可被垃圾 slug 投毒）', () => {
    expect(backendBlog).toMatch(/query = query\.join\(Category\)\.where\(Category\.slug == cat_slug\)/)
    expect(backendBlog).toMatch(/query = query\.join\(Post\.tags\)\.where\(Tag\.slug == tag_slug\)/)
    const keyLine = /make_cache_key\(\s*"posts", "rss"[\s\S]{0,200}?\n\s*\)/.exec(backendBlog)
    expect(keyLine, 'RSS 缓存键必须仍在 posts: 前缀下，否则 invalidate_cache("posts") 清不掉')
      .not.toBeNull()
    expect(keyLine![0]).toContain('cat_slug')
    expect(keyLine![0]).toContain('tag_slug')
  })
})
