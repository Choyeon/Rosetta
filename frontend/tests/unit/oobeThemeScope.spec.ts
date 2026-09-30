/**
 * OOBE 明暗双主题守卫。
 *
 * 起因（真实事故 ×3）：
 *  1. 最初「壁纸 + 深色毛玻璃」固定深色设计 + 语义令牌文字 —— 亮色下深底配深字不可读；
 *  2. 用页根 .oobe-dark 钉死暗色令牌来救 —— 向导失去明暗切换，且与 Tailwind 双 @theme
 *     产物叠加，语义背景类拿到固化亮色值（白底黑字）；
 *  3. 改为 dark: 双轨后，暗色大面玻璃仍是近乎全透的 white/[0.06~0.07] —— 撞上亮色
 *     Bing 壁纸（如麦田）时毛玻璃糊开整卡发白，浅色文字全部不可读（2026-09-30 截图）。
 *
 * 现方案：工具类「亮色值 + dark:暗色值」双轨；**暗色大面玻璃必须用真深色
 * （zinc-950/55~60）压住任意亮度的壁纸**；署名胶囊恒深玻璃；main.css 的 .dark
 * 声明 color-scheme: dark。仅三个壁纸叠加层在页尾 style 块内亮暗各写一套。
 *
 * 本守卫钉住：
 *  1. 页根是 .oobe-root 且不再存在 .oobe-dark 令牌钉死；
 *  2. style 块不再声明任何 CSS 自定义属性（防止有人重新养一套局部色板）；
 *  3. 三个背景层类都带 .dark 覆盖；
 *  4. 暗色大面玻璃的 dark: 分支必须是 zinc-950/black 深色（防「亮壁纸 + 白玻璃」复发）；
 *  5. 暗色系硬编码类全部成对出现（白名单豁免：署名胶囊/日志控制台）；
 *  6. OOBENavbar 挂 ThemeToggle 且品牌文字不硬编码白色；
 *  7. 步骤切换过渡存在且带 prefers-reduced-motion 降级；
 *  8. 模板用到的 oobe.* i18n 键在 zh/en/ja/zh_Hant 四语全部存在。
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

/** 暗色系硬编码 token（词边界不含 /透明度 后缀形态） */
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

/** 暗色大面玻璃回归线：这些 glass 表面的 dark: 分支必须是不透明深色 */
const DARK_SURFACE_PINS: Array<[string, string]> = [
  ['主卡片', 'bg-white/70 dark:bg-zinc-950/60'],
  ['桌面侧栏', 'bg-white/65 dark:bg-zinc-950/55'],
  ['@supports 降级(卡)', 'dark:[@supports_not_(backdrop-filter)]:bg-zinc-950/95'],
  ['下拉弹层', '!bg-white/95 dark:!bg-zinc-950/95']
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

  it('暗色大面玻璃必须是真深色（zinc-950/black），防「亮壁纸 + 白玻璃」复发', () => {
    for (const [name, classes] of DARK_SURFACE_PINS) {
      expect(oobeVue, `${name} 缺少 ${classes}`).toContain(classes)
    }
    // 署名胶囊恒深玻璃（不带 dark: 分支的暗色面）
    expect(oobeVue).toMatch(/rounded-full backdrop-blur-2xl[^"]*bg-zinc-950\/55/)
    // 大面玻璃不允许再出现暗色半透明白分支
    expect(oobeVue).not.toMatch(/dark:bg-white\/\[0\.0[67]\]/)
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

  it('步骤切换过渡存在，且带 prefers-reduced-motion 降级', () => {
    expect(oobeVue).toMatch(/<Transition\s+name="oobe-step"\s+mode="out-in"/)
    expect(styleBlock).toMatch(/\.oobe-step-enter-active/)
    expect(styleBlock).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*\.oobe-step-enter-active/)
  })

  it('模板用到的 oobe.* i18n 键在 zh/en/ja/zh_Hant 四语全部存在', () => {
    const keys = [...new Set([...oobeVue.matchAll(/t\('oobe\.([a-zA-Z0-9]+)'/g)].map(m => m[1]!))]
    expect(keys.length).toBeGreaterThan(50)
    for (const locale of ['zh', 'en', 'ja', 'zh_Hant']) {
      const json = JSON.parse(readFileSync(resolve(root, `i18n/locales/${locale}.json`), 'utf-8')) as Record<string, Record<string, unknown>>
      const oobe = json.oobe ?? {}
      const missing = keys.filter(k => !(k in oobe))
      expect(missing, `${locale}.oobe 缺键`).toEqual([])
    }
  })
})
