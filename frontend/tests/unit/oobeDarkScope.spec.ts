/**
 * OOBE 固定深色令牌守卫。
 *
 * 起因（真实事故）：pages/oobe.vue 是「壁纸 + 深色毛玻璃」的固定深色设计——
 * 表面层大量硬编码 bg-white/[0.07]、border-white/10 等半透明白，文字却走
 * text-foreground / text-muted-foreground 等语义令牌。页面跟随全局明暗切换时，
 * 亮色下 --foreground 变近黑 → 深底配深字，整页不可读（2026-09-30 生产 OOBE 截图）。
 *
 * 修法：页根 .oobe-dark 把全部语义令牌钉死为暗色值（CSS 变量子树继承），
 * OOBENavbar 移除 ThemeToggle（钉死后的页面上它是视觉 no-op，只会误导）。
 *
 * 本守卫钉住两件事：
 *  1. .oobe-dark 的变量值与 main.css 的 .dark 块逐项一致 —— 两个"暗色板"漂移时立即红；
 *  2. OOBENavbar 不再出现 ThemeToggle —— 除非有人真的给 OOBE 做了完整亮色适配。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(__dirname, '../..')
const oobeVue = readFileSync(resolve(root, 'pages/oobe.vue'), 'utf-8')
const navbarVue = readFileSync(resolve(root, 'components/OOBENavbar.vue'), 'utf-8')
const mainCss = readFileSync(resolve(root, 'assets/css/main.css'), 'utf-8')

/** 从 CSS 源文本截取某个块（按"选择器 { ... }"括号配平）的全部 --var: value 声明 */
function extractVarDecls(source: string, selectorPattern: RegExp): Record<string, string> {
  const m = selectorPattern.exec(source)
  if (!m) return {}
  const open = source.indexOf('{', m.index)
  let depth = 0
  let end = open
  for (let i = open; i < source.length; i++) {
    if (source[i] === '{') depth++
    else if (source[i] === '}') {
      depth--
      if (depth === 0) { end = i; break }
    }
  }
  const body = source.slice(open + 1, end)
  const decls: Record<string, string> = {}
  for (const mm of body.matchAll(/--([a-z-]+)\s*:\s*([^;]+);/g)) {
    const name = mm[1]
    const value = mm[2]
    if (name && value) decls[name] = value.trim()
  }
  return decls
}

const oobeScope = extractVarDecls(oobeVue, /\.oobe-dark\s*\{/)
const darkBlock = extractVarDecls(mainCss, /(^|\n)\s*\.dark\s*\{/)

describe('oobe 固定深色令牌', () => {
  it('页根声明 oobe-dark class', () => {
    expect(oobeVue).toMatch(/class="oobe-dark\s/)
  })

  it('.oobe-dark 覆盖了 .dark 块的全部变量，且值逐项一致', () => {
    const darkVars = Object.keys(darkBlock)
    expect(darkVars.length).toBeGreaterThan(30)
    for (const name of darkVars) {
      expect(oobeScope[name], `--${name} 缺失于 .oobe-dark`).toBeDefined()
      expect(oobeScope[name], `--${name} 值与 main.css .dark 漂移`).toBe(darkBlock[name])
    }
  })

  it('.oobe-dark 未引入 .dark 块之外的多余变量（防止两处各养一套）', () => {
    const extra = Object.keys(oobeScope).filter(n => !(n in darkBlock))
    expect(extra).toEqual([])
  })

  it('.oobe-dark 声明 color-scheme: dark（修正原生控件配色）', () => {
    expect(oobeVue).toMatch(/\.oobe-dark\s*\{[^}]*color-scheme:\s*dark/)
  })

  it('OOBENavbar 不含 ThemeToggle（钉死暗色后它是视觉 no-op）', () => {
    expect(navbarVue).not.toMatch(/ThemeToggle/)
  })
})
