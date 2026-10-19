/**
 * 不可索引页的 robots meta 必须出现在**服务端字节**里（静态源码 + 判定函数断言）。
 *
 * 踩过的坑：/login /register /forgot-password /search /account /admin 是 routeRules
 * 精准反选的 ssr:false 页，页面里的 `useNoindexPage()` 只在 hydration 后写 `<head>`，
 * curl 拿到的原始 HTML 一行 robots 都没有。而 robots.txt 恰恰把这些路径从 Disallow
 * 移出了，移出的理由就是"页面自带 noindex，允许抓取才读得到"。对不执行 JS 的抓取器
 * 这个前提不成立 → 空壳页可被收录。修复是 Nitro `render:html` 注入
 * （server/plugins/noindex-shell-meta.nitro.ts）。
 *
 * 本测试守的是**漂移**：新增一个 noindex 页面却忘了登记服务端名单，以前没有任何闸门
 * 看得见（页面单测只看 .vue 源码，SSR 空壳的 HTML 根本不过它）。
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { NOINDEX_SHELL_PREFIXES, needsNoindexShell } from '../../server/utils/noindex-shell'
import { I18N_URL_PREFIXES, stripLocalePathPrefix } from '../../lib/rosetta-themes'

const ROOT = resolve(__dirname, '..', '..')
const shellUtil = readFileSync(resolve(ROOT, 'server/utils/noindex-shell.ts'), 'utf-8')
const plugin = readFileSync(resolve(ROOT, 'server/plugins/noindex-shell-meta.nitro.ts'), 'utf-8')
const useSeo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')

/** pages/ 下所有 .vue（后台整棵 /admin 树由 layouts/admin.vue 统一声明 noindex）。 */
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

/** pages/x/y.vue → /x/y（index 收敛为父路径，动态段原样保留仅供匹配前缀）。 */
function routeOf(pagePath: string): string {
  const rel = pagePath.slice('pages/'.length).replace(/\.vue$/, '')
  const trimmed = rel
    .split('/')
    .map(seg => (seg === 'index' ? '' : seg))
    .filter(Boolean)
    .join('/')
  return `/${trimmed}`
}

/** 声明了 noindex 的公开页路由（useNoindexPage() 或 useSeo({ noindex: true })）。 */
const noindexRoutes = collectPages()
  .filter((p) => {
    const src = readFileSync(resolve(ROOT, p), 'utf-8')
    return src.includes('useNoindexPage(') || /noindex:\s*true/.test(src)
  })
  .map(routeOf)

describe('不可索引页清单', () => {
  it('确实扫到了 noindex 页（清单为空说明扫描器失效）', () => {
    expect(noindexRoutes.length).toBeGreaterThanOrEqual(7)
    expect(noindexRoutes).toContain('/login')
    expect(noindexRoutes).toContain('/register')
    expect(noindexRoutes).toContain('/forgot-password')
    expect(noindexRoutes).toContain('/search')
    expect(noindexRoutes).toContain('/settings')
  })

  it('每一条声明了 noindex 的路由都在服务端名单里', () => {
    for (const route of noindexRoutes) {
      expect(
        needsNoindexShell(route),
        `${route} 声明了 noindex，但原始 HTML 拿不到那行 meta：请把前缀登记进 server/utils/noindex-shell.ts`
      ).toBe(true)
    }
  })

  it('服务端名单里没有僵尸前缀（每条都要对上某个 noindex 页）', () => {
    for (const prefix of NOINDEX_SHELL_PREFIXES) {
      // 后台树的 noindex 声明在 layouts/admin.vue（37 个子页共用一个布局），不在 pages 扫描里
      if (prefix === '/admin') {
        expect(readFileSync(resolve(ROOT, 'layouts/admin.vue'), 'utf-8')).toContain('useNoindexPage(')
        continue
      }
      const live = noindexRoutes.some(r => r === prefix || r.startsWith(prefix + '/'))
      expect(live, `${prefix} 在名单里，但没有任何页面声明 noindex —— 要么补页面，要么删这条`).toBe(true)
    }
  })

  it('后台整棵树（含带语言前缀的形态）都被覆盖', () => {
    for (const p of ['/admin', '/admin/posts', '/admin/docs/api', '/en/admin', '/ja/admin/tools/seo', '/zh_Hant/admin']) {
      expect(needsNoindexShell(p), p).toBe(true)
    }
    expect(readFileSync(resolve(ROOT, 'layouts/admin.vue'), 'utf-8')).toContain('useNoindexPage(')
  })

  it('公开内容页不得被误伤（noindex 泄漏等于自杀）', () => {
    for (const p of [
      '/', '/en', '/ja/series', '/zh_Hant/about',
      '/posts', '/posts/hot', '/posts/some-slug',
      '/categories', '/tags', '/authors/someone', '/archive/2026', '/page/whatever',
      '/guestbook', '/gallery', '/activity', '/friends', '/about',
      // 同前缀但不是子路径：/login-x 是一条独立路由，不能被 /login 前缀吞掉
      '/login-x', '/search-engine', '/accounting', '/settings-panel', '/admin-x'
    ]) {
      expect(needsNoindexShell(p), p).toBe(false)
    }
  })

  it('语言前缀只有 lib/rosetta-themes 一个真源，server 判定与 nuxt.config 都读它', () => {
    // 曾经 server 侧、nuxt.config 镜像表、中间件各写一份 ['\/en','\/ja','\/zh_Hant']：
    // 加语言时漏改任一处都是静默失效（带前缀的页面整批拿不到 noindex）。
    for (const [file, src] of [
      ['nuxt.config.ts', readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')],
      ['server/utils/noindex-shell.ts', shellUtil],
      ['server/utils/spaShellBrand.ts', readFileSync(resolve(ROOT, 'server/utils/spaShellBrand.ts'), 'utf-8')],
      ['server/plugins/spa-serverrendered-zero.nitro.ts',
        readFileSync(resolve(ROOT, 'server/plugins/spa-serverrendered-zero.nitro.ts'), 'utf-8')],
      ['server/routes/robots.txt.get.ts', readFileSync(resolve(ROOT, 'server/routes/robots.txt.get.ts'), 'utf-8')]
    ] as const) {
      expect(src, `${file} 没有从 lib/rosetta-themes 取语言前缀`)
        .toMatch(/from '[^']*lib\/rosetta-themes'/)
      expect(src, `${file} 自己拼了语言前缀清单`).not.toMatch(/en\|ja\|zh_Hant|'\/en',\s*'\/ja'/)
    }
    for (const raw of I18N_URL_PREFIXES) {
      expect(stripLocalePathPrefix(`${raw}/login`), `${raw}/login 没剥前缀`).toBe('/login')
    }
    expect(stripLocalePathPrefix('/')).toBe('/')
    expect(stripLocalePathPrefix('/posts')).toBe('/posts')
  })

  it('查询串不影响判定（/search?q=… 与带前缀形态同样命中）', () => {
    expect(needsNoindexShell('/search?q=%E4%BD%A0%E5%A5%BD')).toBe(true)
    expect(needsNoindexShell('/en/login?redirect=%2Fadmin')).toBe(true)
  })
})

describe('服务端注入实现', () => {
  it('插件里的 meta 与 useSeo 的 NOINDEX_ROBOTS 是同一个口径', () => {
    const content = useSeo.match(/NOINDEX_ROBOTS\s*=\s*'([^']+)'/)?.[1]
    expect(content, 'composables/useSeo.ts 必须导出 NOINDEX_ROBOTS 常量').toBeTruthy()
    expect(plugin).toContain(`content="${content}"`)
    // 全仓只允许一种 noindex 写法：robots.txt 的移出 Disallow 论证依赖 "follow"
    expect(plugin).not.toContain('noindex, nofollow')
    expect(useSeo).not.toMatch(/'noindex, nofollow'/)
  })

  it('注入前先查已有 robots（SSR 页不能出现两条规范）', () => {
    expect(shellUtil).toContain('NOINDEX_SHELL_PREFIXES')
    expect(plugin).toMatch(/hasRobots/)
    expect(plugin).toMatch(/render:html/)
    expect(plugin).toMatch(/beforeResponse/)
    expect(plugin).toMatch(/needsNoindexShell/)
  })

  it('精准反选表里的 ssr:false 路径都在服务端名单覆盖范围内', () => {
    const cfg = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')
    // 取 routeRules 块里的键，过滤出带 ssr: false 的那些（口径见 AGENTS §2.2）
    const spaPaths = [...cfg.matchAll(/'(\/[^']*)':\s*\{[^}]*ssr:\s*false/g)]
      .map(m => m[1])
      .filter((p): p is string => Boolean(p))
      .filter(p => !p.startsWith('/@'))
      .map(p => p.replace(/\/\*\*$/, ''))
    expect(spaPaths.length).toBeGreaterThan(0)
    for (const p of spaPaths) {
      const covered = NOINDEX_SHELL_PREFIXES.some(pre => p === pre || p.startsWith(pre + '/'))
      expect(
        covered,
        `${p} 是 ssr:false 的空壳页，却没有服务端 noindex —— 空壳会以可索引页的身份被抓走`
      ).toBe(true)
    }
  })
})
