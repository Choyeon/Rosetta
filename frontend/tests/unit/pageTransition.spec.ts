/**
 * 页面/布局切换动画契约（静态源码断言）。
 *
 * 这个文件挡的是"顺手把动画调好看一点"造成的两类回归，它们都不会报错：
 *
 *   1. **不得给 pageTransition / layoutTransition 加 `mode`。**
 *      `mode: 'out-in'` 在 SSR 首帧渲染成 Comment 占位 → RouterView 边界 hydration
 *      mismatch → NUXT_E1005 → Vue 强制重建子树（本仓实测过的生产级根因）。
 *      过渡只能是 name-only。
 *   2. **无 mode 的另一半必须由 CSS 兜住。** 同步 in/out 意味着旧页与新页**同时**在
 *      正常流里：旧页还没消失就把新页顶下去，旧节点被移除后新页再弹回原位——表现是
 *      每次切页整屏跳一下、文档高度瞬时翻倍；而那份正在淡出的副本仍带着一整套
 *      链接与按钮，能抢走落在新页上的点击。所以 `*-leave-active` 必须
 *      `position: absolute` + `pointer-events: none`，并用 `width: 100%` 补回
 *      绝对定位丢掉的块级宽度（否则整页 shrink-to-fit 收成窄条）。
 *      布局过渡同一条：外壳是 `min-h-svh` 的整屏容器，双份同流比页面过渡更刺眼。
 *
 *   3. 节奏：离场比进场快（fast 180ms vs base 280ms）。两份同时半透明会让中间帧
 *      糊成一片，让旧的先退干净、新的再落位。
 *   4. reduced-motion 只在 `@layer base` 里做**一次全局归零**，不在每个过渡类上重复写
 *      media 块——那条 `transition-duration: 0.001ms !important` 已经覆盖本文件所有
 *      过渡；这里钉住它还在，是为了让"新增过渡不再补局部降级"成为有依据的决定。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const configSource = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')
const cssSource = readFileSync(resolve(ROOT, 'assets/css/main.css'), 'utf-8')
const defaultLayoutSource = readFileSync(resolve(ROOT, 'layouts/default.vue'), 'utf-8')

/** 取 `app.<key>` 的过渡配置体（`{ ... }` 内部），不存在则返回 null。 */
function transitionConfigBody(key: string): string | null {
  const m = configSource.match(new RegExp(`${key}:\\s*\\{([^}]*)\\}`))
  return m ? m[1] : null
}

/** 取某个 CSS 选择器**最后一次**出现的规则体（同名选择器可能出现在注释里）。 */
function cssRuleBody(selector: string): string {
  const at = cssSource.lastIndexOf(selector)
  expect(at, `main.css 应定义 ${selector}`).toBeGreaterThan(-1)
  const open = cssSource.indexOf('{', at)
  const close = cssSource.indexOf('}', open)
  return cssSource.slice(open + 1, close)
}

/**
 * 取从 `marker` 之后第一个 `{` 开始的平衡括号块体。
 * 注释里出现的 `{ ... }` 都是成对的，所以按字符计数仍然安全。
 */
function braceBlock(source: string, marker: number): string {
  expect(marker, '源码应包含该标记').toBeGreaterThan(-1)
  const open = source.indexOf('{', marker)
  let depth = 0
  for (let i = open; i < source.length; i++) {
    if (source[i] === '{') depth++
    else if (source[i] === '}') {
      depth--
      if (depth === 0) return source.slice(open + 1, i)
    }
  }
  throw new Error('未闭合的花括号块')
}

describe('页面/布局过渡配置：只允许 name', () => {
  it('两个过渡都在，且名字与 CSS 里的类对得上', () => {
    const page = transitionConfigBody('pageTransition')
    const layout = transitionConfigBody('layoutTransition')
    expect(page, 'app.pageTransition 必须保留').not.toBeNull()
    expect(layout, 'app.layoutTransition 必须保留').not.toBeNull()
    expect(page).toContain("'page-fade'")
    expect(layout).toContain("'layout-fade'")
    for (const name of ['page-fade', 'layout-fade']) {
      expect(cssSource, `main.css 缺少 .${name}-enter-active`).toContain(
        `.${name}-enter-active`
      )
    }
  })

  it('配置体里不得出现 mode / appear（out-in 是已证明的水合不匹配根因）', () => {
    for (const [key, body] of [
      ['pageTransition', transitionConfigBody('pageTransition')],
      ['layoutTransition', transitionConfigBody('layoutTransition')]
    ] as const) {
      expect(body, `${key} 缺失`).not.toBeNull()
      expect(body!.toLowerCase(), `${key} 不得带 mode`).not.toMatch(/\bmode\b\s*:/)
      expect(body!.toLowerCase(), `${key} 不得带 appear`).not.toMatch(/\bappear\b\s*:/)
    }
    // 注释里提 out-in 是文档，配置体提 out-in 是回归；这里只按字面量再钉一次配置行。
    expect(configSource).toContain("pageTransition: { name: 'page-fade' }")
    expect(configSource).toContain("layoutTransition: { name: 'layout-fade' }")
  })
})

describe('离场副本必须退出正常流', () => {
  for (const name of ['page-fade', 'layout-fade'] as const) {
    it(`.${name}-leave-active 移出流、不吃点击、保住宽度`, () => {
      const body = cssRuleBody(`.${name}-leave-active`)
      expect(body).toContain('position: absolute')
      expect(body).toContain('pointer-events: none')
      expect(body).toContain('width: 100%')
    })
  }

  it('进场侧不得被顺手 absolute（新页要正常撑开文档高度）', () => {
    expect(cssRuleBody('.page-fade-enter-active')).not.toContain('position:')
    expect(cssRuleBody('.layout-fade-enter-active')).not.toContain('position:')
  }

  it('离场比进场快，页面内容不得两套同时半透明地叠着', () => {
    expect(cssRuleBody('.page-fade-enter-active')).toContain('--motion-duration-base')
    expect(cssRuleBody('.page-fade-leave-active')).toContain('--motion-duration-fast')
  })

  it('页面过渡保留纵向位移、布局过渡只有淡入淡出', () => {
    expect(cssRuleBody('.page-fade-enter-from')).toContain('translateY')
    expect(cssRuleBody('.page-fade-leave-to')).toContain('translateY')
    expect(cssRuleBody('.layout-fade-enter-from,')).not.toContain('translate')
  })
})

describe('reduced-motion 走全局归零，不在每个过渡类上重复', () => {
  const REDUCE = '@media (prefers-reduced-motion: reduce)'
  const reduceBlocks = () => {
    const out: string[] = []
    let at = cssSource.indexOf(REDUCE)
    while (at !== -1) {
      out.push(braceBlock(cssSource, at))
      at = cssSource.indexOf(REDUCE, at + REDUCE.length)
    }
    return out
  }

  it('存在一条通配的全局归零块（过渡类靠它降级，不再各写一份）', () => {
    const global = reduceBlocks().find((b) => b.includes('transition-duration'))
    expect(global, 'main.css 必须有 prefers-reduced-motion 归零块').toBeTruthy()
    expect(global).toContain('*, *::before, *::after')
    expect(global).toContain('transition-duration: 0.001ms !important')
    // delay 必须一起归零，否则 .stagger-* 仍会在 from 帧空白一段——那本身就是动效。
    expect(global).toContain('animation-delay: 0ms !important')
  })

  it('过渡类自身不得再写局部 reduced-motion 覆写（两处口径迟早分叉）', () => {
    for (const block of reduceBlocks()) {
      expect(block).not.toMatch(/\.(page|layout)-fade/)
    }
  })
})

describe('布局外壳不自带第二份页面过渡', () => {
  it('default.vue 不再自己包 <Transition name="page-...">', () => {
    // 页面级过渡是 app.pageTransition 的单源；布局里再包一层会变成双重淡入淡出。
    expect(defaultLayoutSource).not.toMatch(/<Transition[^>]*name="page-/)
    expect(defaultLayoutSource).not.toContain('<NuxtPage')
  })
})
