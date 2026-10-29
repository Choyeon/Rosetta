/**
 * 作者目录页（/authors）的静态契约。
 *
 * nuxt.config 早就给 `/authors` 配了 swr 600，但页面文件不存在——裸 `/authors` 会落进
 * 顶级 catchall `pages/[slug].vue` 被判 404，规则是死的。这一页补上后有三条最容易退化的点：
 * 1. 取数走 useAPI（SSR 期），不是 $fetch + onMounted；
 * 2. 爬虫能读到的链接（卡片 + 分页）必须挂语言前缀，且分页是真 <a href>；
 * 3. 越界页码 301 必须在 app:rendered 里改状态码（AGENTS §2.2.2 同源口径）。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const page = readFileSync(resolve(process.cwd(), 'pages/authors/index.vue'), 'utf8')
const profile = readFileSync(resolve(process.cwd(), 'pages/authors/[username].vue'), 'utf8')
const nuxtConfig = readFileSync(resolve(process.cwd(), 'nuxt.config.ts'), 'utf8')

describe('作者目录页取数契约', () => {
  it('取数走 useAPI 打公开端点，且不出现裸 $fetch', () => {
    expect(page).toContain(`useAPI<{`)
    expect(page).toMatch(/'\/users\/authors'/)
    expect(page).not.toContain('$fetch(')
  })

  it('页码来自 URL 且只发白名单整数（垃圾参数当第 1 页）', () => {
    expect(page).toMatch(/Math\.max\(1, Number\(route\.query\.page\) \|\| 1\)/)
    expect(page).toMatch(/page: currentPage\.value/)
  })

  it('页面保持 SSR', () => {
    expect(page).not.toMatch(/ssr:\s*false/)
    expect(page).toMatch(/definePageMeta\(\{ layout: 'default' \}\)/)
  })
})

describe('作者目录页链接图与 SEO', () => {
  it('卡片链接走 localeHref（SSR href 是爬虫唯一链接图）', () => {
    expect(page).toMatch(/:to="localeHref\(`\/authors\/\$\{a\.username\}`\)"/)
  })

  it('分页是爬虫可达的 <a href>，当前页才是 aria-current 的 span', () => {
    expect(page).toMatch(/const pageHref = \(page: number\) =>/)
    expect(page).toMatch(/applyLocalePrefix\('\/authors', locale\.value\)/)
    expect(page.match(/:href="pageHref\(/g)?.length).toBeGreaterThanOrEqual(3)
    expect(page).toMatch(/aria-current="page"/)
  })

  it('越界页码 301 回裸目录页，且响应头 no-store', () => {
    expect(page).toMatch(/if \(import\.meta\.server\)/)
    expect(page).toMatch(/hooks\.hookOnce\('app:rendered'/)
    expect(page).toMatch(/statusCode = 301/)
    expect(page).toMatch(/'cache-control', 'no-store'/)
  })

  it('canonical 单一来源：页面不自拼 rel=canonical，也不读 useRequestURL', () => {
    expect(page).not.toMatch(/rel:\s*'canonical'/)
    expect(page).not.toMatch(/useRequestURL/)
  })

  it('最近更新时间不依赖 Intl —— 两端 ICU 差异会打出 hydration 文本差异', () => {
    expect(page).toMatch(/getUTCFullYear\(\)/)
    // 只认调用形态：文件头注释里正解释「不要用 Intl/toLocaleString」，按裸子串断会撞上那句诚实否定
    expect(page).not.toMatch(/new Intl\.DateTimeFormat/)
    expect(page).not.toMatch(/\.toLocaleString\(/)
  })

  it('routeRules 的 /authors 规则与页面文件同时存在（缺一即死规则或漏缓存）', () => {
    expect(nuxtConfig).toMatch(/'\/authors':/)
    expect(nuxtConfig).toMatch(/'\/authors\/\*\*':/)
  })
})

describe('作者目录的入口', () => {
  it('作者主页有「浏览全部作者」入口且挂语言前缀', () => {
    expect(profile).toMatch(/localeHref\('\/authors'\)/)
    expect(profile).toMatch(/authors\.browseAll/)
  })
})
