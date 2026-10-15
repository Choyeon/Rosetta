/**
 * 后台 UI 一致性守卫（2026-10 那轮 admin 重构的回归锁）。
 *
 * 三条不变量各自对应一个真实缺陷，不是审美洁癖：
 * 1. 调色板类名（bg-indigo-100 / hover:bg-red-50 / from-purple-500 …）绕过了设计令牌，
 *    表现是「换品牌色、切深色模式时全站跟着变，只有这一块不变」——
 *    用户截图里那类"局部颜色对不上"的成因。令牌在 main.css 里是裸 HSL 三元组，
 *    任何 Tailwind 具名色阶都不在其中。
 * 2. 页级 Tab 必须走 AdminTabList / AdminTabTrigger。历史写法把激活底色写成
 *    `activeTab === 'x' ? 'bg-primary' : ''`，而文字白色写在 `data-[state=active]:` 上，
 *    两个条件来自不同状态源；v-model 初值与 Tabs 默认值一错位就是「白底白字的空白页签」
 *    （/admin/tools/seo 首屏实测）。统一原语后底色与文字同源于 data-state，结构上不可能再分叉。
 * 3. 自带标题区的组件（插件 / 主题管理器）必须用 AdminPageHeader + StatCard，
 *    否则同一个后台里并存 text-xl 与 text-2xl、令牌图标块与 purple 渐变块两种页头。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'

function walk(dir: string, out: string[] = []): string[] {
  let entries: string[]
  try {
    entries = readdirSync(resolve(process.cwd(), dir))
  } catch {
    return out
  }
  for (const name of entries) {
    const full = `${dir}/${name}`
    if (statSync(resolve(process.cwd(), full)).isDirectory()) walk(full, out)
    else if (full.endsWith('.vue')) out.push(full)
  }
  return out
}

const ADMIN_FILES = walk('pages/admin').concat(walk('components/admin'))
const read = (f: string) => readFileSync(resolve(process.cwd(), f), 'utf8')

/** 只扫 class 字面量：分类/标签的 color 字段是用户数据（十六进制选择器值），不是样式类 */
const PALETTE_CLASS = /(?:bg|text|border|from|via|to|ring|fill|stroke)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|[1-9]00)\b/

describe('后台样式只能来自设计令牌', () => {
  it.each(ADMIN_FILES)('%s 不得使用 Tailwind 具名色阶', (file) => {
    const hits = read(file)
      .split('\n')
      .map((line, i) => ({ n: i + 1, line }))
      .filter(x => PALETTE_CLASS.test(x.line) && !x.line.includes('brand-exempt'))
    expect(
      hits,
      `${file} 出现绕过令牌的色阶类，应改用 bg-primary / text-error / bg-error-muted 等语义类；`
      + `确属第三方品牌色的，在该行注明 brand-exempt 与理由：\n`
      + hits.map(x => `  L${x.n}: ${x.line.trim().slice(0, 120)}`).join('\n')
    ).toHaveLength(0)
  })
})

describe('后台页签必须走共享原语', () => {
  it.each(ADMIN_FILES)('%s 不得用 ref 条件式手写激活底色', (file) => {
    const src = read(file)
    const offenders = src
      .split('\n')
      .map((line, i) => ({ n: i + 1, line }))
      .filter(x => /'bg-primary text-primary-foreground'/.test(x.line))
    expect(
      offenders,
      `${file} 的页签激活态由 ref 条件式决定，与 data-[state=active] 的文字色不同源（空白页签成因）；`
      + '改用 <AdminTabList> + <AdminTabTrigger>：\n'
      + offenders.map(x => `  L${x.n}: ${x.line.trim().slice(0, 120)}`).join('\n')
    ).toHaveLength(0)
  })

  it('AdminTabTrigger 必须自带激活底色（这是上面那条断言成立的前提）', () => {
    expect(read('components/admin/AdminTabTrigger.vue')).toContain('data-[state=active]:bg-primary')
  })
})

describe('插件 / 主题管理器不得自带手写页头', () => {
  it.each([
    'components/admin/plugins/PluginManager.vue',
    'components/admin/themes/ThemeManager.vue'
  ])('%s 必须使用 AdminPageHeader 与 StatCard', (file) => {
    const src = read(file)
    expect(src, `${file} 应渲染共享页头`).toContain('<AdminPageHeader')
    expect(src, `${file} 的统计条应走共享 StatCard`).toContain('<StatCard')
    expect(src, `${file} 不得再自带 h2 标题区`).not.toMatch(/<h2[^>]*text-2xl/)
  })
})
