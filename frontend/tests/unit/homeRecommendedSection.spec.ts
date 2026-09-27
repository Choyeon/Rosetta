/**
 * 首页「推荐阅读」契约测试（静态源码断言，不挂载千行页面组件）。
 *
 * 钉住三件容易悄悄回退的事实——任何一条失守，GET /api/blog/posts/recommended
 * 就重新退化成"后端算法就绪、前端零消费方"的死端点：
 *   1. index.vue 确实请求该端点，且缓存键带 locale（否则切语言不刷新）；
 *   2. 与其他首页请求一起并行 await（不做串行 waterfall）；
 *   3. 推荐条目先按本页已展示的 slug 去重，不足 2 条时整段不渲染；
 *   4. home.recommendedTitle 在 zh/en/ja/zh_Hant 四语中均存在。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const homepageSource = readFileSync(resolve(ROOT, 'pages/index.vue'), 'utf-8')
const LOCALES = ['zh', 'en', 'ja', 'zh_Hant'] as const

/** 取某个标识符之后固定长度的源码窗口，避免整文件正则易碎 */
function windowAfter(needle: string, span = 400): string {
  const at = homepageSource.indexOf(needle)
  expect(at, `首页源码应包含 ${needle}`).toBeGreaterThan(-1)
  return homepageSource.slice(at, at + span)
}

describe('首页推荐位接线', () => {
  it('请求推荐端点且缓存键带 locale', () => {
    const block = windowAfter('const recommendedPromise')
    expect(block).toContain('/blog/posts/recommended')
    expect(block).toContain('home:recommended:')
    expect(block).toContain('+ locale.value')
  })

  it('与其他首页请求并行 await，不做串行 waterfall', () => {
    expect(windowAfter('] = await Promise.all([')).toContain('recommendedPromise')
  })

  it('语言切换时随其余请求一起刷新', () => {
    expect(windowAfter('watch(locale', 260)).toContain('refreshRecommended()')
  })

  it('推荐条目按已展示列表去重，区块带「不足 2 条不渲染」守卫', () => {
    expect(windowAfter('const recommendedPosts')).toContain('posts.value')
    expect(homepageSource).toContain('v-if="recommendedPosts.length >= 2"')
  })

  it('推荐区块用语义标题关联，而非裸 div', () => {
    expect(homepageSource).toContain('aria-labelledby="home-recommended-title"')
    expect(homepageSource).toContain('id="home-recommended-title"')
  })

  it.each(LOCALES)('%s 提供 home.recommendedTitle 文案', (locale) => {
    const messages = JSON.parse(
      readFileSync(resolve(ROOT, `i18n/locales/${locale}.json`), 'utf-8')
    ) as Record<string, Record<string, string>>
    const value = messages.home?.recommendedTitle
    expect(typeof value).toBe('string')
    expect((value ?? '').trim().length).toBeGreaterThan(0)
  })
})
