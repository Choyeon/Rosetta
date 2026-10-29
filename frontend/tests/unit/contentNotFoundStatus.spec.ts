/**
 * 内容不存在时的真实 HTTP 状态码契约（静态源码断言）。
 *
 * 实测（生产构建 + 独立实例）：/posts、/categories、/tags、独立页（顶级 catchall 与
 * /page/<slug> 兼容路由）这几类动态详情页对不存在的 slug 全部返回 HTTP 200 的兜底 UI——
 * 后端这些路径明确回 404，前端把状态码吞掉了。WordPress 口径下"不存在的内容"必须是 404，
 * 否则爬虫会把空壳收进索引，而且这些路由带 swr，200 会被缓存成可复用的"正常页"。
 *
 * 本测试钉住这些页都接了 useContentStatus，且没有改用页面内 throw createError
 * （那条路径渲染 error.vue 但响应仍是 200，见 AGENTS §2.3.2）。
 */

import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { isContentMissing } from '../../composables/useContentStatus'

const ROOT = resolve(__dirname, '..', '..')
const helperPath = resolve(ROOT, 'composables/useContentStatus.ts')
const helper = readFileSync(helperPath, 'utf-8')

const PAGES = [
  'pages/posts/[slug].vue',
  'pages/categories/[slug].vue',
  'pages/tags/[slug].vue',
  // 顶级 catchall 才是独立页的真实落地路由（/page/<slug> 只做重定向）：它接住每一条
  // 形如 /任意单段 的 URL，漏了它等于给垃圾 URL 发 200。
  'pages/[slug].vue',
  'pages/page/[slug].vue',
  'pages/series/[slug].vue',
  'pages/authors/[username].vue',
  'pages/archive/[year]/[month].vue',
  // 单年归档：格式合法的年份（/archive/1999）曾对"这一年没有任何文章"回 200 的
  // 空分组页，还被 /archive/** 的 swr 3600 缓存复用 —— WordPress 的 date archive
  // 口径是空年份直接 404。它同时挂着 archive-year 中间件（管格式），两闸门并存。
  'pages/archive/[year]/index.vue'
]

/** 用各自的文案命名空间（authors./series./archive.）而不是 error.notFoundTitle 的页。 */
const CUSTOM_TITLE_PAGES = ['pages/series/[slug].vue', 'pages/authors/[username].vue']

/**
 * 额外挂命名中间件的那一页：中间件只管**年份格式**（把垃圾参数挡在后端 422 之前），
 * 内容是否存在仍由 useContentStatus 判。两类闸门口径见 AGENTS §2.3.2。
 */
const MIDDLEWARE_PAGES = ['pages/archive/[year]/index.vue']

/**
 * 递归列出 pages/ 下所有"URL 带动态段"的公开页。判定不是"文件名含 [`"而是
 * "自己或任一祖先目录名含 [`"：`pages/archive/[year]/index.vue` 的文件名是 index，
 * 但它对应的路由 `/archive/{year}` 同样是动态段，漏判等于把这一页排除在清单之外。
 * 后台页（pages/admin/**）不参与公开索引，整棵子树跳过。
 */
function dynamicPublicPages(dir = 'pages', acc: string[] = [], insideDynamic = false): string[] {
  for (const entry of readdirSync(resolve(ROOT, dir), { withFileTypes: true })) {
    const rel = `${dir}/${entry.name}`
    const dynamic = insideDynamic || entry.name.includes('[')
    if (entry.isDirectory()) {
      if (entry.name === 'admin') continue
      dynamicPublicPages(rel, acc, dynamic)
    } else if (dynamic && entry.name.endsWith('.vue')) {
      acc.push(rel)
    }
  }
  return acc
}

describe('内容页 404 状态码闸门', () => {
  it('公开动态路由页清单：新增一页必须显式归类，不能默认漏掉 404 闸门', () => {
    // 系列详情页就是这条清单该挡住而当时没挡住的漏网之鱼——它渲染了「系列不存在」
    // 兜底 UI，HTTP 却仍是 200，还被 /series/** 的 swr 3600 缓存成可复用页面。
    const listed = [...PAGES].sort()
    expect(dynamicPublicPages().sort()).toEqual(listed)
    // 挂中间件的页也必须在这份清单里（否则它被两套口径同时漏掉）
    for (const rel of MIDDLEWARE_PAGES) {
      expect(PAGES, `${rel} 只登记在中间件清单里，状态码闸门会漏`).toContain(rel)
    }
  })

  it('中间件判定的页面确实挂了命名中间件（不是把闸门整个删了）', () => {
    for (const rel of MIDDLEWARE_PAGES) {
      const src = readFileSync(resolve(ROOT, rel), 'utf-8')
      expect(src, `${rel} 未挂 archive-year 中间件`).toMatch(/middleware:\s*'archive-year'/)
    }
  })

  it('helper 只在服务端改状态码，且只认明确 404 / 成功但空对象', () => {
    expect(existsSync(helperPath)).toBe(true)
    // 注意：needle 不能写成完整的 'import.meta.server' —— vitest 会把这个字面量
    // 当作 define 目标替换成 false，断言就变成了 toContain(false)。
    expect(helper).toContain('import.meta')
    expect(helper).toContain('server) return')
    expect(helper).toContain('useRequestEvent')
    expect(helper).toContain('setResponseStatus')
    // 判定时点必须是 app:rendered：setup 同步期 useFetch payload 还没落值，
    // 在那里读 missing 会把真实页面一起判成 404（第一版就是这么错的）。
    expect(helper).toContain('app:rendered')
    expect(helper).toContain('status === 404')
    // 判定逻辑必须是导出的纯函数（页面兜底 UI 与状态码共用一份口径）
    expect(helper).toMatch(/export function isContentMissing\(error: unknown, missing: boolean\)/)
    expect(helper).toContain('isContentMissing(error.value, missing.value)')
  })

  describe('isContentMissing 判定口径（状态码闸门与页面分支共用）', () => {
    it.each([
      ['后端明确 404', { status: 404 }, false, true],
      ['statusCode 形态', { statusCode: 404 }, false, true],
      ['信封里带状态码', { data: { status: 404 } }, false, true],
      ['请求成功但对象为空', null, true, true],
      ['网络故障（无状态码）', {}, true, false],
      ['5xx', { status: 503 }, true, false],
      ['有内容且无错误', null, false, false],
      ['403 不当成不存在', { status: 403 }, true, false]
    ])('%s → %s', (_label, err, missing, expected) => {
      expect(isContentMissing(err, missing)).toBe(expected)
    })
  })

  it.each(PAGES)('%s 接线 helper，且不用页面内 createError 冒充 404', (rel) => {
    const src = readFileSync(resolve(ROOT, rel), 'utf-8')
    expect(src).toContain('useContentStatus')
    expect(src).toContain('composables/useContentStatus')
    // 反证只针对真实写法：归档页的头部注释里就写着「页面内 throw createError 仍是 HTTP 200」，
    // 用裸 toContain('createError') 会把这条口径说明判成违规。
    expect(src).not.toMatch(/throw\s+createError\(/)
  })

  it.each(PAGES.filter(rel => !CUSTOM_TITLE_PAGES.includes(rel)))(
    '%s 缺内容时标题走 404 文案，不再伪造 slug 标题',
    (rel) => {
      const src = readFileSync(resolve(ROOT, rel), 'utf-8')
      expect(src).toContain('error.notFoundTitle')
      // 旧口径是 `pickLocalized(...) || slug.value || ''`：404 页的 <title> 变成一串
      // 假装是分类名的乱码。WordPress 的 404 标题就是"页面不存在"。
      expect(src).not.toMatch(/\|\|\s*slug\.value \|\| ''/)
    }
  )

  it('用自有文案的页仍与状态码闸门共用 isContentMissing（标题不与响应码互相矛盾）', () => {
    for (const rel of CUSTOM_TITLE_PAGES) {
      const src = readFileSync(resolve(ROOT, rel), 'utf-8')
      expect(src, `${rel} 没引入共用判定`).toContain('isContentMissing')
      expect(src, `${rel} 的标题分支没与闸门共用判定`).toMatch(
        /if \(([A-Za-z]*[Nn]otFound|isContentMissing\()\b/
      )
    }
    for (const loc of ['zh', 'en', 'ja', 'zh_Hant']) {
      const messages = JSON.parse(
        readFileSync(resolve(ROOT, `i18n/locales/${loc}.json`), 'utf-8')
      ) as Record<string, Record<string, string>>
      expect(messages.series?.notFoundTitle, `${loc} 缺 series.notFoundTitle`).toBeTruthy()
    }
  })

  it.each(PAGES)('%s 把同一条判定喂给 useSeo 的 noindex（响应码 / robots / canonical 同源）', (rel) => {
    const src = readFileSync(resolve(ROOT, rel), 'utf-8')
    // 实测：404 的 /posts/zzz、/series/zzz、/archive/2099 全都写着
    // `index, follow, max-image-preview:large…` 并自带一条指向自己的 canonical +
    // hreflang 集群。状态码说"没了"，head 说"收我"——两份矛盾信号里爬虫挑哪份不可控。
    expect(src, `${rel} 未把 noindex 接到闸门判定上`).toMatch(
      /noindex:\s*(?:[A-Za-z]*[Nn]otFound|computed\(\(\) => isContentMissing)/
    )
    // 不许硬编码：noindex: true 会把正常内容的这一页一起禁掉
    expect(src, `${rel} 的 noindex 是常量，会把真实内容页一起禁索引`).not.toMatch(/noindex:\s*true/)
    // 且 noindex 必须与 useContentStatus 同源（同一个 *NotFound 计算属性）
    expect(src).toMatch(/useContentStatus\(/)
  })

  it('四语都有 error.notFoundTitle 文案', () => {
    for (const loc of ['zh', 'en', 'ja', 'zh_Hant']) {
      const messages = JSON.parse(
        readFileSync(resolve(ROOT, `i18n/locales/${loc}.json`), 'utf-8')
      ) as Record<string, Record<string, string>>
      expect(messages.error?.notFoundTitle, `${loc} 缺 error.notFoundTitle`).toBeTruthy()
    }
  })
})

/**
 * 作者主页（/authors/{username}）的"不存在"分支。
 *
 * 后端对「查无此人」与「作者关了公开资料」统一回 404，页面必须同步换成不存在文案：
 * 旧实现只看 loadError，404 会落到「加载失败，请稍后重试」——等于一边告诉爬虫这个 URL
 * 没了，一边告诉用户刷新一下就能看到。
 */
describe('作者主页的 404 分支', () => {
  const rel = 'pages/authors/[username].vue'
  const src = readFileSync(resolve(ROOT, rel), 'utf-8')

  it('UI 分支与状态码闸门共用同一个判定函数', () => {
    expect(src).toMatch(
      /import \{ isContentMissing, useContentStatus \} from '~~\/composables\/useContentStatus'/
    )
    expect(src).toContain('isContentMissing(profileError.value, profileMissing.value)')
    expect(src).toContain('useContentStatus(profileError, profileMissing)')
  })

  it('notFound 分支排在 loadError 之前，且隐藏作者头', () => {
    const notFoundAt = src.indexOf('v-else-if="notFound"')
    const loadErrorAt = src.indexOf('v-else-if="loadError"')
    expect(notFoundAt).toBeGreaterThan(-1)
    expect(notFoundAt).toBeLessThan(loadErrorAt)
    expect(src).toMatch(/<header\s+v-if="!notFound"/)
    // 兜底文案必须是"不存在"，不能复用重试提示
    expect(src).toMatch(/t\('authors\.notFoundTitle'/)
  })

  it('不存在时的标题走 404 文案，不由用户名伪造', () => {
    expect(src).toMatch(/if \(notFound\.value\) return t\('authors\.notFoundTitle'\)/)
  })

  it('四语都有 authors.notFoundTitle / notFoundDesc', () => {
    for (const loc of ['zh', 'en', 'ja', 'zh_Hant']) {
      const messages = JSON.parse(
        readFileSync(resolve(ROOT, `i18n/locales/${loc}.json`), 'utf-8')
      ) as Record<string, Record<string, string>>
      expect(messages.authors?.notFoundTitle, `${loc} 缺 authors.notFoundTitle`).toBeTruthy()
      expect(messages.authors?.notFoundDesc, `${loc} 缺 authors.notFoundDesc`).toBeTruthy()
    }
  })
})

/**
 * 不存在态的面板必须有 h1。
 *
 * 实测（生产构建）：`/posts/<不存在>` 的 404 有 `<h1>页面不存在</h1>`（文章页的 h1 无条件
 * 渲染，缺内容时文本换成 404 文案），而 `/series/<不存在>`、`/archive/1999/01`、`/tags/<不存在>`、
 * `/categories/<不存在>` 的面板里一个 h1 都没有——面板只写了 `error.notFoundDesc` 一段说明，
 * 标题层级从 h2/h5 起跳，读屏按标题跳转时拿不到"这一页是什么"。
 * 系列页那处更隐蔽：用的是 `AlertTitle`，而它渲染的是 **h5**。
 *
 * 判据：在 not-found 分支的静态窗口内出现 `<h1`。窗口取"到下一个兄弟分支开头"，避免靠
 * 猜字符数——每个面板的说明段长度都可能变。唯一例外是文章详情页：它的 h1 无条件渲染在
 * 面板之前（保证 SSR → Hydrate 结构一致），缺内容时文本自己换成 404 文案，所以它要求
 * "h1 在分支之前"而不是"在分支之内"。
 */
describe('不存在态的面板必须有 h1 标题', () => {
  /** [页面, 分支判据, 'before' = h1 无条件渲染在分支之前] */
  const PANELS: [string, string, 'before'?][] = [
    ['pages/posts/[slug].vue', 'postNotFound', 'before'],
    ['pages/categories/[slug].vue', 'catNotFound'],
    ['pages/tags/[slug].vue', 'tagNotFound'],
    ['pages/[slug].vue', 'pageNotFound'],
    ['pages/page/[slug].vue', 'compatPageNotFound'],
    ['pages/series/[slug].vue', 'seriesNotFound'],
    ['pages/authors/[username].vue', 'notFound'],
    ['pages/archive/[year]/[month].vue', 'monthNotFound'],
    ['pages/archive/[year]/index.vue', 'yearNotFound']
  ]

  it('清单与 404 闸门页清单一一对应（新增一页必须同时登记）', () => {
    expect(PANELS.map(([rel]) => rel).sort()).toEqual([...PAGES].sort())
  })

  it.each(PANELS)('%s 的 %s 面板里有 h1', (rel, marker, before) => {
    const src = readFileSync(resolve(ROOT, rel), 'utf-8')
    const markerAt = src.search(new RegExp(`v-(?:else-)?if="${marker}"`))
    expect(markerAt, `${rel} 找不到 v-if="${marker}" 分支`).toBeGreaterThan(-1)
    if (before) {
      const h1Abs = src.indexOf('<h1')
      expect(h1Abs, `${rel} 声明 h1 在分支之前无条件渲染，但文件里没有 h1`).toBeGreaterThan(-1)
      expect(h1Abs, `${rel} 的 h1 落在分支之后，不再是"无条件渲染"`).toBeLessThan(markerAt)
      return
    }
    // 只看分支之后的部分：页面正常态自己也有一个 h1，拿全文 indexOf 会取到它。
    const branch = src.slice(markerAt)
    const h1Rel = branch.indexOf('<h1')
    // 下一个兄弟分支（<template v-else / v-if / v-else-if>）之前的范围就是本面板
    const nextBranchAt = branch.slice(1).search(/<template\s+v-(?:else|if|else-if)=/)
    const window = nextBranchAt > 0 ? nextBranchAt : 1200
    expect(
      h1Rel > 0 && h1Rel < window,
      `${rel} 的 404 面板没有 h1（只有说明段），标题层级从 h2/h5 起跳`
    ).toBe(true)
  })
})
