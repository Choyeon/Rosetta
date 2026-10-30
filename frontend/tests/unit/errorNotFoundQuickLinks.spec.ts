/**
 * 404 兜底页的站内快捷入口（批次 #221）。
 *
 * 背景：生产上未命中路由的 404 页只有「返回首页」，访客除了回首页没有第二条出路，
 * 而 error.vue 是 layout:false 的根级兜底页——它不经任何布局，导航栏/侧边栏都不在。
 * 三条约束：
 *  1. 只在 404 出现（401/403 与 5xx 各有自己的动作按钮，不该混入站内导航）。
 *  2. 两个渲染分支（极简主题 .ap-error / 默认 .error-page）都要有，否则换主题即丢。
 *  3. 链接走 localePath()，语言前缀与站内其它页面同源；原生 <a>（整页刷新清错误态）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'error.vue'), 'utf-8')
const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const

const block = (name: string): string =>
  src.match(new RegExp(`const ${name} = [\\s\\S]*?\\n\\}`))?.[0] ?? ''

describe('404 快捷入口', () => {
  it('只在 404 产出，且四条入口都走 localePath', () => {
    const fn = block('quickLinks')
    expect(fn).toContain('statusCode.value !== 404')
    for (const path of ['/posts', '/categories', '/tags', '/archive']) {
      expect(fn).toContain(`localePath('${path}')`)
    }
  })

  it('用原生 <a> 而非 NuxtLink（跳转要连带清掉错误态）', () => {
    const anchors = src.match(/v-for="link in quickLinks"[\s\S]{0,200}?<\/a>/g) ?? []
    expect(anchors.length).toBe(2)
    for (const a of anchors) expect(a).toContain(':href="link.to"')
    expect(anchors.some(a => a.includes('class="ap-error-link"'))).toBe(true)
    expect(anchors.some(a => a.includes('class="error-btn ghost"'))).toBe(true)
    expect(src).not.toMatch(/NuxtLink[\s\S]{0,80}quickLinks/)
  })

  it('两个渲染分支各有一条导航行', () => {
    expect(src.match(/v-if="quickLinks.length"/g)?.length).toBe(2)
  })

  it('i18n 未就绪时四条文案有中文兜底', () => {
    for (const key of ['nav.posts', 'nav.categories', 'nav.tags', 'nav.archive']) {
      expect(src).toContain(`'${key}':`)
    }
  })

  it('四语 nav 键都存在（缺一个就退回裸 key）', () => {
    for (const code of locales) {
      const json = JSON.parse(
        readFileSync(resolve(ROOT, `i18n/locales/${code}.json`), 'utf-8')
      ) as { nav: Record<string, string> }
      for (const key of ['posts', 'categories', 'tags', 'archive']) {
        expect(json.nav[key], `${code}.nav.${key}`).toBeTruthy()
      }
    }
  })
})
