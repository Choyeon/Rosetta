/**
 * SPA 空壳页标题契约（站点设置 → 浏览器标签页）。
 *
 * 表现过的 bug：/login /register /search /account /admin 是精准反选的 ssr:false 路径，
 * Nitro 只吐构建期空壳，`<title>` 来自 nuxt.config 的常量 'Rosetta'；后台改了站点名、
 * 填了「SEO · 页面默认标题」，这六条路径的标签页标题一个字都不变（curl 实测），
 * 因为 default_title 只活在"本页无标题"分支里，而那条分支被这个构建期占位永久占掉。
 *
 * 两道补齐都必须钉住：
 *  1. 服务端：spa-shell-brand.nitro.ts 按 /settings/public 改写空壳里的 `<title>`（curl 面）；
 *  2. 客户端：app.vue 与 site-title.global.ts 认这个占位＝"无标题"（hydration 后不回退）。
 * 少了 (2)，服务端补的标题会在 JS 起来后被 "Rosetta · 站点名" 顶掉；
 * 少了 (1)，禁用 JS / 爬虫与首帧用户看到的还是构建期常量。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  buildShellTitle,
  isSpaShellPath,
  rewriteShellTitle,
  SPA_SHELL_PREFIXES
} from '../../server/utils/spaShellBrand'
import { brandFloorTitle, pickBrandSubtitle, SPA_SHELL_TITLE_PLACEHOLDER } from '../../lib/utils'

const appVue = readFileSync(resolve(process.cwd(), 'app.vue'), 'utf8')
const titlePlugin = readFileSync(resolve(process.cwd(), 'plugins/site-title.global.ts'), 'utf8')
const useSite = readFileSync(resolve(process.cwd(), 'composables/useSite.ts'), 'utf8')
const nuxtConfig = readFileSync(resolve(process.cwd(), 'nuxt.config.ts'), 'utf8')
const shellPlugin = readFileSync(
  resolve(process.cwd(), 'server/plugins/spa-shell-brand.nitro.ts'),
  'utf8'
)

describe('SPA 壳页标题占位的单源', () => {
  it('常量与 nuxt.config 的 app.head.title 是同一个字面量', () => {
    const m = /head:\s*\{[\s\S]{0,600}?\btitle:\s*'([^']+)'/.exec(nuxtConfig)
    expect(m, 'nuxt.config 里 app.head.title 必须是单引号字面量').not.toBeNull()
    expect(m![1]).toBe(SPA_SHELL_TITLE_PLACEHOLDER)
  })

  it('两处标题权威都把占位当作"本页无标题"', () => {
    expect(appVue).toContain('SPA_SHELL_TITLE_PLACEHOLDER')
    expect(appVue).toMatch(/t && t !== SPA_SHELL_TITLE_PLACEHOLDER/)
    expect(titlePlugin).toMatch(/t === SPA_SHELL_TITLE_PLACEHOLDER/)
  })
})

describe('isSpaShellPath', () => {
  it('覆盖 ssr:false 反选表，且带语言前缀同样命中', () => {
    for (const p of ['/login', '/register', '/forgot-password', '/search', '/account', '/admin']) {
      expect(isSpaShellPath(p), p).toBe(true)
      expect(isSpaShellPath(`/en${p}/x`), `/en${p}/x`).toBe(true)
    }
    expect(isSpaShellPath('/admin/posts/1')).toBe(true)
    expect(isSpaShellPath('/login?next=/account')).toBe(true)
  })

  it('公开 SSR 页与同前缀噪声路径不得命中', () => {
    for (const p of ['/', '/posts', '/posts/1', '/about', '/guestbook', '/oobe', '/login-x', '/settings']) {
      expect(isSpaShellPath(p), p).toBe(false)
    }
    expect(isSpaShellPath('')).toBe(false)
  })

  it('名单与 §2.2 的 ssr:false 反选表一致（/oobe 已改 SSR，不得回流）', () => {
    expect(SPA_SHELL_PREFIXES).toEqual([
      '/login',
      '/register',
      '/forgot-password',
      '/search',
      '/account',
      '/admin'
    ])
  })
})

describe('brandFloorTitle：副标题与站名同值不得拼成「X · X」', () => {
  it('同值只留站名（含空白差异）', () => {
    expect(brandFloorTitle('Choyeon Blog', 'Choyeon Blog')).toBe('Choyeon Blog')
    expect(brandFloorTitle('Choyeon Blog', '  Choyeon Blog  ')).toBe('Choyeon Blog')
    expect(buildShellTitle('Choyeon Blog', 'Choyeon Blog')).toBe('Choyeon Blog')
  })

  it('不同值仍按「站名 · 副标题」拼接，空副标题只留站名，站名缺失回落 Rosetta', () => {
    expect(brandFloorTitle('Choyeon Blog', '穿越语言的边界')).toBe('Choyeon Blog · 穿越语言的边界')
    expect(brandFloorTitle('Choyeon Blog', '   ')).toBe('Choyeon Blog')
    expect(brandFloorTitle('', '副标题')).toBe('Rosetta · 副标题')
  })

  it('候选挑选：跳过与站名同值的项，不会把真正的副标题整条丢掉', () => {
    expect(pickBrandSubtitle('Choyeon Blog', 'Choyeon Blog', '分享知识与灵感'))
      .toBe('分享知识与灵感')
    expect(pickBrandSubtitle('Choyeon Blog', 'Choyeon Blog', '')).toBe('Choyeon Blog')
    expect(pickBrandSubtitle('Choyeon Blog', '', undefined, '  ')).toBe('')
  })

  it('两处取「站名 + 候选副标题」的口子都过 pickBrandSubtitle', () => {
    expect(useSite).toContain('pickBrandSubtitle')
    expect(
      readFileSync(resolve(process.cwd(), 'server/plugins/spa-shell-brand.nitro.ts'), 'utf8')
    ).toContain('pickBrandSubtitle')
  })

  it('四处拼接全部走同一个 helper（线上 /login 曾出现「Choyeon Blog · Choyeon Blog」）', () => {
    for (const [label, source] of [
      ['app.vue', appVue],
      ['plugins/site-title.global.ts', titlePlugin],
      ['composables/useSite.ts', useSite],
      ['server/utils/spaShellBrand.ts', readFileSync(
        resolve(process.cwd(), 'server/utils/spaShellBrand.ts'),
        'utf8'
      )]
    ] as const) {
      expect(source, label).toContain('brandFloorTitle')
      // 旧写法：`${name} · ${sub}` / `${siteName} · ${siteSub}` 直接拼副标题
      expect(source, label).not.toMatch(/\$\{\s*(?:site)?[nN]ame\s*\} · \$\{\s*(?:site)?[sS]ub(?:title)?\s*\}/)
    }
  })
})

describe('buildShellTitle / rewriteShellTitle', () => {
  it('标题拼接与客户端 titleTemplate 同口径', () => {
    expect(buildShellTitle('Rosetta Blog', '穿越语言的边界')).toBe('Rosetta Blog · 穿越语言的边界')
    expect(buildShellTitle('Rosetta Blog', '')).toBe('Rosetta Blog')
    expect(buildShellTitle('', '   ')).toBe('Rosetta')
  })

  it('只改 `<title>`，其余原样', () => {
    const html = '<html><head><title>Rosetta</title><meta name="robots" content="noindex, follow"></head><body>x</body></html>'
    const next = rewriteShellTitle(html, '我的站 · 默认标题')
    expect(next).toContain('<title>我的站 · 默认标题</title>')
    expect(next).toContain('name="robots"')
    expect(next).not.toContain('Rosetta')
  })

  it('标题文本必须转义，不能把设置值当标签写进去', () => {
    const next = rewriteShellTitle('<title>Rosetta</title>', 'A & B <script>x</script>')
    expect(next).toBe('<title>A &amp; B &lt;script&gt;x&lt;/script&gt;</title>')
  })

  it('幂等：同值重复改写不产生第二个 title，也不改动内容', () => {
    const html = '<head><title>站点 · 副标题</title></head>'
    const once = rewriteShellTitle(html, '站点 · 副标题')
    expect(once).toBe(html)
    expect(rewriteShellTitle(once, '站点 · 副标题')).toBe(html)
    expect((once.match(/<title/g) ?? []).length).toBe(1)
  })

  it('缺 `<title>` 或没有新标题时原样返回（后端不可用＝保留构建期壳）', () => {
    expect(rewriteShellTitle('<head><meta charset="utf-8"></head>', '站点')).toContain('charset')
    expect(rewriteShellTitle('<title>Rosetta</title>', '')).toBe('<title>Rosetta</title>')
  })
})

describe('spa-shell-brand 插件接线', () => {
  it('render:html 与 beforeResponse 两道钩子都挂，且都过 isSpaShellPath 过滤', () => {
    expect(shellPlugin).toMatch(/hook\(\s*'render:html'/)
    expect(shellPlugin).toMatch(/hook\(\s*'beforeResponse'/)
    expect(shellPlugin.match(/isSpaShellPath\(/g)?.length).toBeGreaterThanOrEqual(2)
  })

  it('品牌源是 /settings/public（分组真源），并带超时与失败留空', () => {
    expect(shellPlugin).toMatch(/\/settings\/public/)
    expect(shellPlugin).toMatch(/timeout: BRAND_TIMEOUT_MS/)
    expect(shellPlugin).toMatch(/catch \{\s*\n\s*\/\/[^\n]*\n\s*return ''/)
    expect(shellPlugin).toContain('seo.default_title')
  })

  it('进程内缓存 TTL 不得长到让"保存后标题不跟"（后端 PATCH 已即时清自己的缓存）', () => {
    expect(shellPlugin).toMatch(/BRAND_TTL_MS = 15_000/)
  })
})
