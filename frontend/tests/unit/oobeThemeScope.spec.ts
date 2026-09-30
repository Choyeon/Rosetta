/**
 * OOBE 明暗双主题守卫。
 *
 * 起因（真实事故 ×2）：
 *  1. pages/oobe.vue 最初是「壁纸 + 深色毛玻璃」固定深色设计，表面层硬编码半透明白、
 *     文字走语义令牌 —— 跟随全局明暗切换时亮色下深底配深字，整页不可读；
 *  2. 当时用页根 .oobe-dark 把全部语义令牌钉死为暗色值来救，结果向导失去明暗切换，
 *     且子树钉死与 Tailwind 双 @theme 产物叠加，语义背景类反而拿到固化亮色值（白底黑字）。
 *
 * 现方案：页面完整跟随全局明暗主题 —— 工具类一律「亮色值 + dark:暗色值」双轨，
 * 由 <html>.dark 驱动；ThemeToggle 回到 OOBENavbar；仅三个壁纸叠加层
 * （渐变兜底/暗角/网格）在页尾 style 块内亮暗各写一套。
 *
 * 本守卫钉住：
 *  1. 页根是 .oobe-root 且不再存在 .oobe-dark 令牌钉死；
 *  2. style 块不再声明任何 CSS 自定义属性（防止有人重新养一套局部色板）；
 *  3. 三个背景层类都带 .dark 覆盖；
 *  4. 暗色系硬编码类在 oobe.vue 中全部成对出现（每处都有 dark: 前缀版本），
 *     已知例外（署名胶囊 = 恒深玻璃、日志控制台 = 终端风）以白名单显式豁免；
 *  5. OOBENavbar 挂了 ThemeToggle，且品牌文字不再硬编码白色。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(__dirname, '../..')
const oobeVue = readFileSync(resolve(root, 'pages/oobe.vue'), 'utf-8')
const navbarVue = readFileSync(resolve(root, 'components/OOBENavbar.vue'), 'utf-8')

/** 页尾 <style> 块 */
const styleBlock = (() => {
  const m = /<style>([\s\S]*?)<\/style>/.exec(oobeVue)
  return m?.[1] ?? ''
})()

/** 已知例外：署名胶囊是恒深玻璃（压在壁纸上），内部白系类不需要 dark: 成对 */
const PILL_EXCEPTIONS = [
  'rounded-full text-white/85 hover:bg-white/10 hover:text-white disabled:opacity-40',
  'text-[12px] font-medium text-white/90 hover:bg-white/10 hover:text-white'
]

/** 暗色系硬编码 token（词边界不含 /透明度 后缀形态，后者单独列出） */
const DARK_TONE_TOKENS = [
  'bg-white/[0.03]',
  'bg-white/[0.04]',
  'bg-white/[0.05]',
  'bg-white/[0.08]',
  'bg-white/5',
  'bg-white/10',
  'bg-white/15',
  'border-white/10',
  'border-white/15',
  'ring-white/10',
  'ring-white/15',
  'text-emerald-200',
  'text-emerald-300',
  'text-teal-300',
  'text-cyan-300',
  'text-sky-300',
  'text-rose-300',
  'text-rose-200',
  'text-amber-300',
  'text-amber-200'
]

function stripExceptions(src: string): string {
  let out = src
  for (const ex of PILL_EXCEPTIONS) out = out.split(ex).join('')
  return out
}

describe('oobe 明暗双主题', () => {
  it('页根声明 oobe-root，且不再存在 oobe-dark', () => {
    expect(oobeVue).toMatch(/class="oobe-root\s/)
    expect(oobeVue).not.toMatch(/oobe-dark/)
  })

  it('style 块不再声明任何 CSS 自定义属性（禁止局部色板复活）', () => {
    expect(styleBlock).not.toMatch(/^\s*--[a-z-]+\s*:/m)
  })

  it('三个壁纸叠加层类都带 .dark 覆盖', () => {
    for (const cls of ['oobe-bg-fallback', 'oobe-vignette', 'oobe-grid']) {
      expect(oobeVue).toMatch(new RegExp(`\\.${cls}\\s*\\{`))
      expect(oobeVue).toMatch(new RegExp(`\\.dark \\.${cls}\\s*\\{`))
      expect(oobeVue).toMatch(new RegExp(`class="[^"]*\\b${cls}\\b`))
    }
  })

  it('暗色系硬编码类全部成对出现（豁免白名单之外每处都带 dark: 前缀版本）', () => {
    const src = stripExceptions(oobeVue)
    for (const token of DARK_TONE_TOKENS) {
      const guarded = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![\\w/])'
      const all = src.match(new RegExp(`(?<![\\w-])${guarded}`, 'g')) ?? []
      const paired = src.match(new RegExp(`(?<![\\w-])dark:(?:[a-zA-Z][a-zA-Z0-9-]*:)*!?${guarded}`, 'g')) ?? []
      expect(all.length, `${token} 共 ${all.length} 处，其中仅 ${paired.length} 处带 dark: 前缀`).toBe(paired.length)
    }
  })

  it('OOBENavbar 挂载 ThemeToggle（向导内可切换明暗）', () => {
    expect(navbarVue).toMatch(/<ThemeToggle\s*\/>/)
  })

  it('OOBENavbar 品牌文字走 text-foreground，不再硬编码白色', () => {
    expect(navbarVue).not.toMatch(/text-white/)
    expect(navbarVue).toMatch(/text-foreground/)
  })
})
