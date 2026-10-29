/**
 * 公开顶层页面必须有站内入口（SSR 的 href 才是爬虫看得到的链接图，AGENTS §2.3.3 第 2 条）。
 *
 * 起因（2026-10-29 线上实测）：`/posts/hot` 是一个完整可用的页面，但首页 + 页脚的 SSR HTML 里
 * `href="/posts/hot"` 出现 **0 次**——站点上线后没有任何入口能走到热度榜，sitemap 之外的内链图里
 * 也不存在这个 URL。`/sponsor` 是反向的坑：未配置收款方式时它自己声明 noindex 占位
 * （pages/sponsor.vue 头注释），无条件挂页脚入口等于把访客引向一张空白页。
 *
 * 本测试守两件事：
 * 1. 页脚把这两类页面分开处理——热点榜恒定存在，捐助入口跟 `donate.methods` 走；
 * 2. 新增一个公开顶层页面却既没进顶栏也没进页脚时直接红，逼作者在 allowlist 里写清
 *    "入口由谁负责"（详情页 / 后台导航 / 顶栏按钮），而不是留下一个没人能点到的 URL。
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const header = readFileSync(resolve(ROOT, 'components/AppHeader.vue'), 'utf-8')
const footer = readFileSync(resolve(ROOT, 'components/AppFooter.vue'), 'utf-8')

const LOCALES = ['zh', 'en', 'ja', 'zh_Hant'] as const
const localeOf = (code: string) =>
  JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${code}.json`), 'utf-8')) as Record<
    string,
    Record<string, unknown>
  >

/** pages/ 下所有 .vue（后台整棵树不参与：入口在 AdminSidebar）。 */
function collectPages(dir = 'pages', acc: string[] = []): string[] {
  for (const entry of readdirSync(resolve(ROOT, dir))) {
    const rel = `${dir}/${entry}`
    if (statSync(resolve(ROOT, rel)).isDirectory()) {
      if (rel === 'pages/admin') continue
      collectPages(rel, acc)
    } else if (entry.endsWith('.vue')) {
      acc.push(rel)
    }
  }
  return acc
}

/** pages/x/index.vue → /x；pages/x.vue → /x。 */
function routeOf(pagePath: string): string {
  const rel = pagePath.slice('pages/'.length).replace(/\.vue$/, '')
  const segs = rel.split('/').filter(s => s !== 'index')
  return `/${segs.join('/')}`
}

/** 私有 / 登录态页面：入口在登录菜单或登录后的跳转里，不属于页脚职责。 */
const PRIVATE_PREFIXES = ['/account', '/settings', '/login', '/register', '/forgot-password', '/oobe']

/**
 * 入口由别处负责的公开页。每一条必须写明"谁负责"，不允许空理由：
 * - `/search`：顶栏放大镜按钮走客户端 `go('/search')`，页面本身是 ssr:false 空壳，没有可渲染的 href；
 * - `/series`：入口在文章详情页的系列卡片与后台导航配置里；站点没有系列时不该逼运营者挂一个空列表入口。
 */
const ENTRY_ELSEWHERE: Record<string, string> = {
  '/search': '顶栏搜索按钮 go(/search)（ssr:false，无 href）',
  '/series': '文章详情页的系列卡片 + 后台导航配置'
}

const publicTopLevel = collectPages()
  .map(routeOf)
  .filter(route => !route.includes('['))
  .filter(route => !PRIVATE_PREFIXES.some(prefix => route === prefix || route.startsWith(`${prefix}/`)))

const linkedInShell = (route: string) =>
  header.includes(`to: '${route}'`) || footer.includes(`to: '${route}'`)

describe('公开页面的入口可达性', () => {
  it('每个公开顶层页面要么进顶栏/页脚，要么在 allowlist 里写明入口由谁负责', () => {
    const orphans = publicTopLevel.filter(
      route => route !== '/' && !linkedInShell(route) && !(route in ENTRY_ELSEWHERE)
    )
    expect(orphans, `这些页面没有任何站内入口：${orphans.join(', ')}`).toEqual([])
  })

  it('allowlist 不养僵尸条目：写进去的页面必须真实存在', () => {
    const stale = Object.keys(ENTRY_ELSEWHERE).filter(route => !publicTopLevel.includes(route))
    expect(stale, `allowlist 指向了不存在的页面：${stale.join(', ')}`).toEqual([])
  })

  it('热点榜恒定挂在页脚（它不依赖任何内容或开关）', () => {
    expect(footer).toContain('to: \'/posts/hot\'')
  })

  it('捐助入口跟 donate 配置走：未配置收款方式时页面是 noindex 占位，不该有入口', () => {
    expect(footer).toContain('link.to !== \'/sponsor\' || site.donate.value.methods.length > 0')
    // 两处渲染（桌面 / 移动）都必须走过滤后的列表，否则过滤只在一处生效
    const rendered = footer.match(/v-for="link in visibleSiteLinks"/g) ?? []
    expect(rendered.length).toBe(2)
    expect(footer).not.toContain('v-for="link in siteLinks"')
  })

  it('页脚两个新入口的四语标签都存在', () => {
    for (const code of LOCALES) {
      const dict = localeOf(code)
      expect(dict.footer?.hot, `${code}.footer.hot 缺失`).toBeTruthy()
      expect(dict.footer?.sponsor, `${code}.footer.sponsor 缺失`).toBeTruthy()
    }
  })
})
