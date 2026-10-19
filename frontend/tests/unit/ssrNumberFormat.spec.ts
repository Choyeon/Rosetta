/**
 * SSR 面数字格式化单源守卫。
 *
 * 表现：文章详情页字数写成 `wordCount.toLocaleString()`（无 locale 参数）时，
 * 分组按**各自运行环境**的默认 locale 走 —— 服务端是 `1,234`，德语/俄语浏览器是
 * `1.234`，两端文本不一致 → hydration mismatch；这一页还带 swr，差异会被固化成
 * TTL 内所有人拿到的 HTML 字节。首页当年正是靠写死 `'en-US'` 躲过这一坑，
 * 现在把口径提成了 `lib/utils::formatCount` 单源。
 *
 * 扫描面 = SSR 页与其组件（pages/components 里排除 `admin`，也排除 routeRules 反选的
 * SPA 面：`/login` `/register` `/forgot-password` `/search` `/account` `/oobe`）。
 * SPA 只在浏览器渲染，跟随浏览器 locale 分组是期望行为，不算违规。
 */
import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync } from 'node:fs'
import process from 'node:process'
import { formatCount } from '@/lib/utils'

const ROOT = process.cwd().replace(/[\\/]$/, '')
const SCAN_DIRS = ['pages', 'components']
const SPA_PATHS = ['/login', '/register', '/forgot-password', '/search', '/account', '/oobe']

function walk(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = `${dir}/${entry.name}`
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue
      out.push(...walk(full))
    } else if (/\.(vue|ts)$/.test(entry.name)) out.push(full)
  }
  return out
}

describe('formatCount', () => {
  it('分组固定 en-US，不受运行环境默认 locale 影响', () => {
    expect(formatCount(58100)).toBe('58,100')
    expect(formatCount(900)).toBe('900')
  })

  it('null / undefined / NaN / Infinity 一律回 0 而不是 "NaN"', () => {
    expect(formatCount(null)).toBe('0')
    expect(formatCount(undefined)).toBe('0')
    expect(formatCount(Number.NaN)).toBe('0')
    expect(formatCount(Number.POSITIVE_INFINITY)).toBe('0')
  })
})

describe('SSR 面不得出现无 locale 的 Intl 数字格式化', () => {
  it('pages/** 与 components/**（排除后台与 SPA 反选页）里没有裸 toLocaleString()', () => {
    const bare = /\.toLocale(?:String|DateString|TimeString)\(\s*\)/u
    const offenders: string[] = []
    for (const sub of SCAN_DIRS) {
      for (const file of walk(`${ROOT}/${sub}`)) {
        const rel = file.replace(`${ROOT}/`, '')
        const relNoExt = rel.replace(/\.(vue|ts)$/u, '')
        if (relNoExt.includes('/admin')) continue
        // 反选页按**路由形态**比对：pages/account/index.vue → /account/index
        const route = relNoExt.startsWith('pages/')
          ? `/${relNoExt.slice('pages/'.length)}`
          : `/${relNoExt}`
        if (SPA_PATHS.some(p => route === p || route.startsWith(`${p}/`))) continue
        if (bare.test(readFileSync(file, 'utf8'))) offenders.push(rel)
      }
    }
    expect(
      offenders,
      `这些 SSR 文件用了无 locale 的 toLocale*()，两端分组/顺序会不一致，请改 formatCount 或显式传 locale：${offenders.join(', ')}`
    ).toEqual([])
  })

  it('首页与文章详情确实走 formatCount 单源', () => {
    const home = readFileSync(`${ROOT}/pages/index.vue`, 'utf8')
    const post = readFileSync(`${ROOT}/pages/posts/[slug].vue`, 'utf8')
    expect(home).toMatch(/import \{ formatCount \} from '~~\/lib\/utils'/u)
    expect(post).toMatch(/import \{ formatCount \} from '~~\/lib\/utils'/u)
    expect(home).toContain('formatCount(siteStats.total_words)')
    expect(post).toContain('formatCount(wordCount)')
    expect(post).toContain('formatCount(charCount)')
  })
})
