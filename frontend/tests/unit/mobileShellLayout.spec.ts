/**
 * 移动端外壳三件事的静态契约：版心留白、表格不撑破文档、汉堡按钮不被裁掉。
 *
 * 三条都曾是"只在 375px 才暴露"的缺陷，改回任何一种旧写法都不会让 lint/typecheck 变红，
 * 所以钉在这里：
 *  1) Tailwind v4 的 `.container` 不带任何水平 padding（v3 的 container.padding 配置项也没了）。
 *     全站 29 个页面写的是 `class="container py-16"`，于是在窄屏上正文/按钮直接贴住屏幕左右缘。
 *     留白由 main.css 的 @layer base 兜住；页面自带的 `px-*` 工具类在 utilities 层，仍然覆盖它。
 *  2) Markdown 表格列数多时，表格 min-content 宽度把整份文档撑出横向滚动条
 *     （表现是整页可左右拖、标题被推出屏幕），所以表格自己当滚动容器。
 *  3) 顶栏控件区全是 shrink-0：品牌 + 搜索 + 明暗 + 语言 + 登录 + 注册 + 汉堡在 375px
 *     总宽约 500px，溢出时被裁掉的是汉堡 = 移动端没有导航。语言与登录/注册收进抽屉，
 *     ClientOnly 的 SSR 占位必须跟着同一批条件走，否则首屏仍按 500px 排版再弹一次。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (rel: string): string => readFileSync(resolve(process.cwd(), rel), 'utf8')
const mainCss = read('assets/css/main.css')
const apCss = read('themes/astro-paper-inspired/style.css')
const header = read('components/AppHeader.vue')

describe('版心横向留白', () => {
  it('.container 必须自带 padding-inline，不能只居中', () => {
    const rule = mainCss.slice(mainCss.indexOf('  .container {'), mainCss.indexOf('}', mainCss.indexOf('  .container {')))
    expect(rule).toMatch(/margin-inline: auto;/)
    expect(rule).toMatch(/padding-inline: clamp\(1rem, 4vw, 1\.5rem\);/)
  })
})

describe('富文本表格不撑破文档', () => {
  it('main.css 的表格自己是横向滚动容器', () => {
    const rule = mainCss.slice(mainCss.indexOf('.prose-shadcn table {'), mainCss.indexOf('}', mainCss.indexOf('.prose-shadcn table {')))
    expect(rule).toMatch(/display: block;/)
    expect(rule).toMatch(/overflow-x: auto;/)
  })

  it('极简主题覆写了 table，也必须带上同一条滚动口径', () => {
    const rule = apCss.slice(
      apCss.indexOf('article[class*="prose-shadcn"] table {'),
      apCss.indexOf('}', apCss.indexOf('article[class*="prose-shadcn"] table {'))
    )
    expect(rule).toMatch(/display: block;/)
    expect(rule).toMatch(/overflow-x: auto;/)
  })
})

describe('顶栏窄屏', () => {
  it('语言切换与登录/注册在 <sm 收进抽屉，给汉堡让出宽度', () => {
    expect(header).toMatch(/class="hidden sm:flex items-center">\s*<LocaleSwitcher \/>/)
    expect(header).toMatch(/class="ml-1 hidden sm:flex items-center gap-2"/)
  })

  it('SSR 占位行跟着同一批显示条件，且同样在 <sm 隐藏', () => {
    const fallback = header.slice(header.indexOf('<template #fallback>'), header.indexOf('</template>', header.indexOf('<template #fallback>')))
    expect(fallback).toMatch(/v-if="showSearch"/)
    expect(fallback).toMatch(/v-if="showDarkModeToggle"/)
    expect(fallback).toMatch(/v-if="showLanguageSwitch"/)
    expect(fallback).toMatch(/v-if="showRegister"/)
    // 占位不得再写死 4 个 size-10（那是不管开关都排 250px 的旧写法）
    expect((fallback.match(/size-10/g) ?? []).length).toBe(2)
    expect(fallback).toMatch(/hidden sm:flex/)
  })
})

describe('reduced-motion 全局闸门', () => {
  it('除了 duration，delay 也要归零：否则 stagger + fill-mode both 的内容会先空白再一批批弹出', () => {
    const gate = mainCss.slice(
      mainCss.indexOf('@media (prefers-reduced-motion: reduce)'),
      mainCss.indexOf('}', mainCss.indexOf('animation-iteration-count'))
    )
    expect(gate).toMatch(/animation-duration: 0\.001ms !important;/)
    expect(gate).toMatch(/animation-delay: 0ms !important;/)
    expect(gate).toMatch(/transition-delay: 0ms !important;/)
  })
})
