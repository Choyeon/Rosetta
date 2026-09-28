/**
 * 作者主页（/authors/[username]）的静态契约。
 *
 * 这一页的存在理由是"后端就绪、前端零消费"的最后一个 users 缺口，
 * 而它最容易退化的三点都必须钉住：
 * 1. 取数走 useAPI（SSR 期取数），不是裸 $fetch + onMounted —— 否则首屏白屏、爬虫拿不到内容；
 * 2. 列表用 `?author=` 过滤而不是"先取 id 再取列表"的依赖链 —— 依赖链会让 SSR 首帧拿不到列表；
 * 3. 404 判定只挂在**资料**请求上（列表为空只是"没发文"），且必须走 useContentStatus，
 *    不能在页面里 throw createError（AGENTS §2.3.2：那样响应仍是 200）。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const page = readFileSync(resolve(process.cwd(), 'pages/authors/[username].vue'), 'utf8')
const postPage = readFileSync(resolve(process.cwd(), 'pages/posts/[slug].vue'), 'utf8')

describe('作者主页取数契约', () => {
  it('资料与列表都用 useAPI，且不出现裸 $fetch', () => {
    expect(page).toContain('useAPI<AuthorProfile>(')
    expect(page).toMatch(/`\/users\/username\/\$\{username\.value\}`/)
    expect(page).toContain(`useAPI<{`)
    expect(page).not.toContain('$fetch(')
  })

  it('列表用 author query 过滤，不做 username→id 的依赖式二次请求', () => {
    expect(page).toMatch(/'\/blog\/posts'/)
    expect(page).toMatch(/author: username\.value/)
    // 依赖链的形态（先取资料再拼 id）不应该出现在这一页
    expect(page).not.toMatch(/user_id|profile\.value\?\.id/)
  })

  it('404 闸门只看资料请求，列表为空不判 404', () => {
    expect(page).toMatch(
      /useContentStatus\(profileError, computed\(\(\) => !profile\.value\?\.username\)\)/
    )
    expect(page).not.toMatch(/createError/)
  })

  it('页面保持 SSR（反选只由 routeRules 负责，页面内不写 ssr:false）', () => {
    expect(page).not.toMatch(/ssr:\s*false/)
    expect(page).toMatch(/definePageMeta\(\{ layout: 'default' \}\)/)
  })

  it('加入年份不依赖 Intl —— 两端 ICU 差异会打出 hydration 文本差异', () => {
    expect(page).toMatch(/getUTCFullYear\(\)/)
    expect(page).not.toMatch(/Intl\.DateTimeFormat/)
  })
})

/** noUncheckedIndexedAccess 下顶层段落索引结果可能 undefined，统一收口一次。 */
function section(data: Record<string, Record<string, string>>, name: string): Record<string, string> {
  return data[name] ?? {}
}

describe('作者主页可达性与文案', () => {
  it('文章详情作者卡链接到作者主页，缺 username 时退回纯文本（不留死链）', () => {
    expect(postPage).toMatch(/const authorUrl = computed\(\(\) =>/)
    expect(postPage).toMatch(/:to="authorUrl"/)
    expect(postPage).toMatch(/v-if="authorUrl"/)
    expect(postPage).toMatch(/v-else/)
  })

  it('四语 authors.* 键集合一致，且分页导航有 aria-label 文案', () => {
    const expected = ['emptyTitle', 'eyebrow', 'github', 'joined', 'posts', 'website']
    for (const loc of ['zh', 'en', 'ja', 'zh_Hant']) {
      const data = JSON.parse(
        readFileSync(resolve(process.cwd(), `i18n/locales/${loc}.json`), 'utf8')
      ) as Record<string, Record<string, string>>
      expect(Object.keys(section(data, 'authors')).sort()).toEqual(expected)
      expect(section(data, 'common').pagination).toBeTypeOf('string')
      expect(section(data, 'post').viewAuthorProfile).toBeTypeOf('string')
    }
    expect(page).toMatch(/:aria-label="t\('common\.pagination'/)
  })

  it('外链展示（网站/GitHub）必须带 rel=noopener noreferrer', () => {
    const blankLinks = page.match(/target="_blank"/g) ?? []
    const guarded = page.match(/rel="noopener noreferrer"/g) ?? []
    expect(blankLinks.length).toBeGreaterThan(0)
    expect(guarded.length).toBe(blankLinks.length)
  })
})
