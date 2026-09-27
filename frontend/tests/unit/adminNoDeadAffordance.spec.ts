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
})
