/**
 * SSR 外壳里 reka-ui 根组件的 ClientOnly 契约（静态源码断言）。
 *
 * 根因写在 nuxt.config.ts 的 nitro 段：rolldown-vite 的 SSR 产物把主 app 的 vue runtime
 * 以绝对路径内联、而 reka-ui 走 external 的 bare import，运行时存在两份 vue，
 * provide/inject 跨实例静默失效 → reka 根组件在服务端只剩一个空注释占位，
 * 客户端却渲染出真正的触发器节点，水合时整页报
 * 「Hydration node mismatch: rendered on server: #comment」。
 * 上游没有干净开关（三条修复路径都试过），所以约定是应用层隔离：**凡会出现在 SSR
 * 外壳里的 reka 根组件，必须关在 ClientOnly 里**。这条一旦被改回裸写，报错只出现在
 * 浏览器控制台，构建与单测都不会红，因此在这里钉住。
 */

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOT = resolve(__dirname, '..', '..')
const REKA_ROOTS = /<(DropdownMenu|Popover|Tooltip|Sheet|Dialog|AlertDialog|HoverCard|ContextMenu|Select|Switch)\b/g

function clientOnlySpans(src: string): Array<[number, number]> {
  const spans: Array<[number, number]> = []
  for (const m of src.matchAll(/<ClientOnly\b[^>]*>/g)) {
    const end = src.indexOf('</ClientOnly>', m.index!)
    spans.push([m.index!, end === -1 ? src.length : end])
  }
  return spans
}

function outsideClientOnly(file: string): string[] {
  const src = readFileSync(resolve(ROOT, file), 'utf-8')
  const spans = clientOnlySpans(src)
  const out: string[] = []
  for (const m of src.matchAll(REKA_ROOTS)) {
    const at = m.index!
    if (!spans.some(([s, e]) => at > s && at < e)) out.push(m[0])
  }
  return out
}

describe('SSR 外壳组件的 reka 根组件都在 ClientOnly 内', () => {
  it.each([
    'components/AppHeader.vue',
    'components/LocaleSwitcher.vue'
  ])('%s', (file) => {
    expect(outsideClientOnly(file), `${file} 有 reka 根组件落在 ClientOnly 之外`).toEqual([])
  })

  it('SiteNavSidebar 本身就是一个 reka Sheet，所以挂载点必须在 ClientOnly 里', () => {
    const header = readFileSync(resolve(ROOT, 'components/AppHeader.vue'), 'utf-8')
    const spans = clientOnlySpans(header)
    const mounts = [...header.matchAll(/<SiteNavSidebar\b/g)].map(m => m.index!)
    expect(mounts.length, '顶栏至少要有一个侧边栏导航挂载点').toBeGreaterThan(0)
    for (const at of mounts) {
      expect(spans.some(([s, e]) => at > s && at < e), 'SiteNavSidebar 必须在 ClientOnly 内挂载').toBe(true)
    }
  })
})
