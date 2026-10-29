/**
 * Admin 页签激活态配方契约（2026-10 生产缺陷回归）。
 *
 * 缺陷：/admin/tools/seo 首个页签渲染成"空白胶囊"。根因不是图标没渲染，而是
 * 白字压在白底上——页面用**无变体**的 `bg-primary` 去覆盖 shadcn TabsTrigger 基线里
 * **带变体**的 `data-[state=active]:bg-background`：
 *   - tailwind-merge 按「修饰符不同」判定为两组，两条类都留在 class 串里；
 *   - 于是由 CSS 特异性裁决，带 `[data-state=active]` 属性选择器的基线胜出 → 白底；
 *   - 而 `data-[state=active]:text-primary-foreground` 与基线同修饰符，被正常合并 → 白字。
 *
 * 口径：覆盖激活态必须走同修饰符的 `data-[state=active]:*`，让 cn() 真正做冲突消解。
 * 第一组用例直接跑 twMerge（本仓 class 合并的真实引擎）证明这条口径成立、且旧写法确实失效；
 * 第二组静态扫源码，防止有人在页面里把旧配方复制回来。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { twMerge } from 'tailwind-merge'

/** 与 components/ui/tabs/TabsTrigger.vue 基线中的冲突对（只取与本契约相关的部分） */
const BASE_TRIGGER = 'data-[state=active]:bg-background data-[state=active]:text-foreground'

/** 旧配方：无变体 bg-primary + 同变体 text-primary-foreground（生产上隐形的那一种） */
const BROKEN_RECIPE = 'data-[state=active]:text-primary-foreground bg-primary text-primary-foreground'

/** 新配方：bg 与 text 同修饰符 */
const CANONICAL_RECIPE = 'data-[state=active]:bg-primary data-[state=active]:text-primary-foreground'

const tokens = (s: string) => s.split(/\s+/).filter(Boolean)
const has = (s: string, t: string) => tokens(s).includes(t)

/** 递归收集 .vue（两条静态守卫共用） */
function walkDir(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name)
    if (entry.isDirectory()) out.push(...walkDir(p))
    else if (entry.name.endsWith('.vue')) out.push(p)
  }
  return out
}

describe('tailwind-merge 对激活态覆盖的裁决', () => {
  it('旧配方：基线白底存活（bg-primary 修饰符不同，挤不掉它）→ 这就是生产缺陷的一半', () => {
    const merged = twMerge(BASE_TRIGGER, BROKEN_RECIPE)
    expect(has(merged, 'data-[state=active]:bg-background')).toBe(true)
    expect(has(merged, 'data-[state=active]:text-foreground')).toBe(false)
  })

  it('新配方：同修饰符才能把基线白底挤掉', () => {
    const merged = twMerge(BASE_TRIGGER, CANONICAL_RECIPE)
    expect(has(merged, 'data-[state=active]:bg-background')).toBe(false)
    expect(has(merged, 'data-[state=active]:bg-primary')).toBe(true)
    expect(has(merged, 'data-[state=active]:text-foreground')).toBe(false)
    expect(has(merged, 'data-[state=active]:text-primary-foreground')).toBe(true)
  })
})

describe('AdminTabTrigger / AdminTabList 是唯一配方来源', () => {
  const triggerSource = readFileSync(resolve(process.cwd(), 'components/admin/AdminTabTrigger.vue'), 'utf8')
  const listSource = readFileSync(resolve(process.cwd(), 'components/admin/AdminTabList.vue'), 'utf8')

  it('AdminTabTrigger 的激活底色与激活文字同修饰符', () => {
    expect(triggerSource).toContain('data-[state=active]:bg-primary')
    expect(triggerSource).toContain('data-[state=active]:text-primary-foreground')
  })

  it('两个原语存在且各自只包一层 shadcn 组件', () => {
    expect(triggerSource).toContain('~~/components/ui/tabs')
    expect(listSource).toContain('~~/components/ui/tabs')
  })
})

describe('AdminTabList 的高度由内容撑开（竖直滚动条回归）', () => {
  // 缺陷（2026-10-29 线上实测，仪表盘「流量总览 / 互动 & 内容」那一排）：
  // `overflow-x-auto` 按 CSS 规范会把 `overflow-y` 的 visible 当成 auto 计算，
  // 于是容器一旦比 `padding + 页签高度` 矮就多出一条竖直滚动条。
  // 当时是 h-8（32px）容器 + p-1.5（12px）+ h-7（28px）页签 = 40px 内容装进 32px。
  // 默认那档同样矮了 4px（h-11=44 对 12+36），只是首页那排才刚好被看见。
  const LIST_BASE = 'h-auto w-full justify-start gap-1 overflow-x-auto overflow-y-hidden rounded-xl bg-muted/50 p-1.5'
  const listSource = readFileSync(resolve(process.cwd(), 'components/admin/AdminTabList.vue'), 'utf8')

  it('写死的高度一定会赢过 h-auto，所以基线不能指望自己撑开', () => {
    const merged = twMerge(LIST_BASE, 'h-8')
    expect(has(merged, 'h-8')).toBe(true)
    expect(has(merged, 'h-auto')).toBe(false)
    // 矮一档的正确做法是改 padding：它与基线同组，能被 cn() 正常替换掉。
    const viaPadding = twMerge(LIST_BASE, 'p-0.5')
    expect(has(viaPadding, 'p-0.5')).toBe(true)
    expect(has(viaPadding, 'p-1.5')).toBe(false)
  })

  it('基线是 h-auto + overflow-y-hidden，且不含任何固定高度', () => {
    expect(listSource).toContain('h-auto')
    expect(listSource).toContain('overflow-y-hidden')
    expect(listSource).not.toMatch(/cn\(\s*'[^']*?h-\d/)
  })

  it('没有任何使用方给 AdminTabList 传固定高度（只能传 padding 调档位）', () => {
    const roots = [resolve(process.cwd(), 'pages/admin'), resolve(process.cwd(), 'components')]
    const offenders: string[] = []
    const seen: string[] = []

    for (const root of roots) {
      for (const f of walkDir(root)) {
        const src = readFileSync(f, 'utf8')
        // 每个用法写在同一行；跨行拆属性的写法本守卫看不见，所以另有一条"必须含
        // <AdminTabList"的正向计数，防止正则整体失配后这条用例变成恒真。
        for (const line of src.split('\n')) {
          if (!/<AdminTabList\b/.test(line)) continue
          seen.push(f)
          const cls = /class="([^"]*)"/.exec(line)?.[1] ?? ''
          if (/(?:^|\s)h-\d/.test(cls)) offenders.push(`${f}: ${cls}`)
        }
      }
    }

    expect(seen.length, '一处 AdminTabList 都没扫到 = 扫描器失配，不是通过').toBeGreaterThan(6)
    expect(offenders, `页签容器写死了高度：${offenders.join(' | ')}`).toEqual([])
  })
})

describe('后台页面不得再内联页签激活配方', () => {
  const adminRoot = resolve(process.cwd(), 'pages/admin')
  const files = walkDir(adminRoot)

  it('没有任何页面再直接 import shadcn 的 TabsTrigger（必须经 AdminTabTrigger）', () => {
    const offenders: string[] = []
    for (const f of files) {
      const src = readFileSync(f, 'utf8')
      const importLine = /import\s*\{([^}]*)\}\s*from\s*'~~\/components\/ui\/tabs'/.exec(src)
      if (!importLine) continue
      const names = importLine[1]!.split(',').map(s => s.trim()).filter(Boolean)
      if (names.includes('TabsTrigger') || names.includes('TabsList')) {
        offenders.push(f.replace(adminRoot, 'pages/admin'))
      }
    }
    expect(offenders, `以下页面仍自带 TabsList/TabsTrigger：${offenders.join(', ')}`).toEqual([])
  })

  it('没有任何页面残留"无变体 bg-primary 覆盖激活态"的隐形配方', () => {
    const offenders: string[] = []
    for (const f of files) {
      const src = readFileSync(f, 'utf8')
      // 触发条件是 TabsTrigger 上同时出现 active 文字变体与裸 bg-primary
      if (/<TabsTrigger[\s\S]{0,400}?bg-primary/.test(src) && src.includes('data-[state=active]:text')) {
        offenders.push(f.replace(adminRoot, 'pages/admin'))
      }
    }
    expect(offenders, `隐形页签配方回归：${offenders.join(', ')}`).toEqual([])
  })
})
