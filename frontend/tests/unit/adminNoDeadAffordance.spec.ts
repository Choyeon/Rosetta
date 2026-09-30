/**
 * Admin UI 死壳门禁：后台不得存在"看起来能点、点了只弹占位提示"的控件。
 *
 * 起因：ThemeManager 的「子主题：继承自 X」曾写成 `href="#"` + `@click.prevent` 弹
 * `stubToast('父主题占位')`。Rosetta 没有主题继承实现面（parent_theme 只在清单里存着），
 * 该链接永远没有真实去处，却给了链接 + 箭头 + hover 变色全套可点暗示；
 * 键盘用户 Tab 上去回车只会得到一条"占位"toast。属于 Accessibility 与信任双输。
 *
 * 用静态源码扫描而不是 mount：admin 组件普遍依赖 Nuxt 自动导入（useI18n / apiFetch /
 * 布局），mount 需要大量桩，且"没有真实跳转目标"这件事本来就只能从源码字面判定。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOTS = ['components/admin', 'pages/admin', 'layouts/admin.vue']

function collectVue(dir: string, out: string[] = []): string[] {
  const abs = resolve(process.cwd(), dir)
  let entries: string[]
  try {
    entries = readdirSync(abs)
  } catch {
    return out // layouts/admin.vue 是文件，走不到这里
  }
  for (const name of entries) {
    const full = `${dir}/${name}`
    if (statSync(resolve(process.cwd(), full)).isDirectory()) collectVue(full, out)
    else if (name.endsWith('.vue')) out.push(full)
  }
  return out
}

const sources: { file: string, text: string }[] = []
for (const root of ROOTS) {
  const abs = resolve(process.cwd(), root)
  try {
    if (statSync(abs).isFile()) sources.push({ file: root, text: readFileSync(abs, 'utf8') })
    else for (const f of collectVue(root)) sources.push({ file: f, text: readFileSync(resolve(process.cwd(), f), 'utf8') })
  } catch {
    /* 目录不存在时跳过 —— 但下面的总数断言会兜住"扫到 0 个文件"的假绿 */
  }
}

/**
 * 判定只看"活代码"：模板注释与 JS 注释里描述历史缺陷的字面量不是回归。
 * 不剥注释的话，本仓第一次修复留下的解释性注释会立刻把自己判成失败。
 */
function stripComments(text: string): string {
  return text
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^[ \t]*\/\/.*$/gm, '')
}

const codeOnly = sources.map(s => ({ file: s.file, text: stripComments(s.text) }))

describe('Admin UI · 无死壳控件契约', () => {
  it('扫描面非空（防门禁因路径漂移静默失效）', () => {
    expect(sources.length, '必须扫到后台组件与页面').toBeGreaterThan(40)
  })

  it('后台不得出现 href="#" 假链接', () => {
    const hits = codeOnly
      .filter(s => /href=["']#["']/.test(s.text))
      .map(s => s.file)
    expect(hits, `以下文件仍有无目标的锚链接：${hits.join(', ')}`).toEqual([])
  })

  it('后台不得保留 stub 提示函数（点击只弹「占位」= 功能缺失伪装成已完成）', () => {
    const hits = codeOnly
      .filter(s => /stubToast|toast\.\w+\([^)]*占位/.test(s.text))
      .map(s => s.file)
    expect(hits, `以下文件仍有占位型交互：${hits.join(', ')}`).toEqual([])
  })

  it('父主题继承只作信息展示，不再伪装成可点条目', () => {
    const themeManager = codeOnly.find(s => s.file.endsWith('themes/ThemeManager.vue'))
    expect(themeManager, 'ThemeManager.vue 必须在扫描面内').toBeDefined()
    expect(themeManager!.text).toContain('theme.parent_theme')
    expect(themeManager!.text).not.toMatch(/parent_theme[\s\S]{0,200}@click/)
  })

  /**
   * 侧栏折叠开关的位置契约（踩过的坑）：
   * 曾经的形态是三颗按钮分头管同一份状态 ——
   *   · AdminSidebar 顶部一颗 ChevronLeft（仅展开态可见）
   *   · AdminSidebar 底部一颗 ChevronRight（仅收起态可见）
   *   · AdminHeader 左侧一颗汉堡 MenuIcon（md:hidden，仅 <768px 可见）
   * 后果有两个：(1) 同一个 toggle 在收起/展开之间会从上跳到下；(2) 布局在 ≥1280px
   * 才展开侧栏，而汉堡在 ≥768px 就隐藏了，于是 768–1280px 之间 **没有任何可点开关**，
   * 自动收起后无法再展开。
   * 修法是把控制权收回 AdminHeader 的一颗常驻按钮，这里把该结构锁死。
   */
  it('侧栏折叠开关唯一且在 AdminHeader，侧栏不得再有 toggle', () => {
    const header = codeOnly.find(s => s.file.endsWith('admin/AdminHeader.vue'))
    const sidebar = codeOnly.find(s => s.file.endsWith('admin/AdminSidebar.vue'))
    expect(header, 'AdminHeader.vue 必须在扫描面内').toBeDefined()
    expect(sidebar, 'AdminSidebar.vue 必须在扫描面内').toBeDefined()

    // AdminHeader 里必须恰好一个 aria-controls="admin-sidebar" 的开关
    const headerToggles = [...header!.text.matchAll(/aria-controls=["']admin-sidebar["']/g)]
    expect(headerToggles.length, '折叠开关必须在 AdminHeader 内且唯一').toBe(1)
    expect(header!.text, '开关必须是全断点可见，禁止再加 md:hidden').not.toMatch(
      /aria-controls=["']admin-sidebar["'][\s\S]{0,400}?md:hidden|md:hidden[\s\S]{0,400}?aria-controls=["']admin-sidebar["']/
    )

    // AdminSidebar 不再自己管折叠（只剩 v-model 受控），因此不得出现 toggle 类按钮
    expect(sidebar!.text, '侧栏不得再放置折叠/展开按钮').not.toMatch(/aria-label=["'](收起|展开)侧边导航/)
    expect(sidebar!.text, '侧栏仍应保留受控的 collapsed prop').toContain('update:collapsed')
  })
})
