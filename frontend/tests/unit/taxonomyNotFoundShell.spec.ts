/**
 * 分类 / 标签详情页的 404 口径（静态源码断言）。
 *
 * 踩过的坑：不存在的分类/标签 slug 返回 HTTP 404（`useContentStatus` 改的状态码），
 * 页面却落进 `loadError` 分支——因为列表请求（`/blog/posts?category=<不存在的值>`）
 * 照样成功、只是空，真正缺席的是详情请求，而模板没有"不存在"这条分支。
 * 线上实测：`/categories/no-such-cat` 显示「页面不存在 / 0 篇文章 / 文章列表加载失败」，
 * `/tags/no-such-tag` 的 h1 还把标签徽章与标题并排渲染成「页面不存在 页面不存在」。
 *
 * 修法口径（四条，改回任一条都会复现）：
 *   1) 新增 `v-else-if="catNotFound"` / `v-else-if="tagNotFound"` 分支，且必须排在
 *      `loadError` 之前——不存在不是临时故障，刷新一百次也不会好；
 *   2) 该分支只给一块面板（文案 + 返回列表 + 返回首页），不得复用「加载失败」文案；
 *   3) 头部「N 篇文章」计数在不存在时不显示：0 篇是对"这个分类存在但空"的描述；
 *   4) 标签页的徽章在不存在时撤掉，否则同一个标题并排出现两次。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

interface Case {
  file: string
  flag: string
  listPath: string
  countKey: string
}

const cases: Case[] = [
  { file: 'pages/categories/[slug].vue', flag: 'catNotFound', listPath: '/categories', countKey: 'categories.posts' },
  { file: 'pages/tags/[slug].vue', flag: 'tagNotFound', listPath: '/tags', countKey: 'tags.posts' }
]

describe.each(cases)('$file 的 404 口径', ({ file, flag, listPath, countKey }) => {
  const src = readFileSync(resolve(__dirname, '..', '..', file), 'utf-8')

  it('不存在分支存在，且排在「加载失败」分支之前', () => {
    const notFound = src.search(new RegExp(`<template\\s+v-else-if="${flag}"`))
    const loadError = src.search(/<template\s+v-else-if="loadError"/)
    expect(notFound, `缺少 ${flag} 分支`).toBeGreaterThan(0)
    expect(loadError).toBeGreaterThan(0)
    expect(notFound).toBeLessThan(loadError)
  })

  it('不存在面板给文案与两条出口，不冒充加载失败', () => {
    const start = src.search(new RegExp(`<template\\s+v-else-if="${flag}"`))
    const end = src.indexOf('</template>', start)
    const panel = src.slice(start, end)
    expect(panel).toContain('error.notFoundDesc')
    expect(panel).toContain(`localeHref('${listPath}')`)
    expect(panel).toContain('error.backHome')
    expect(panel).not.toContain('admin.posts.loadFailed')
  })

  it('头部计数在不存在时不渲染', () => {
    const pill = src.slice(src.indexOf(`{{ postCount }} {{ t('${countKey}'`) - 400, src.indexOf(`{{ postCount }} {{ t('${countKey}'`))
    expect(pill).toContain(`v-if="!${flag}"`)
  })
})

describe('tags/[slug].vue 标题去重', () => {
  const src = readFileSync(resolve(__dirname, '..', '..', 'pages/tags/[slug].vue'), 'utf-8')

  it('徽章与纯文本标题互斥：同一时刻只有一份标签名（线上曾是「Python Python」）', () => {
    const h1Start = src.indexOf('<h1')
    const h1End = src.indexOf('</h1>', h1Start)
    const h1 = src.slice(h1Start, h1End)
    expect(h1).toContain('v-if="!tagNotFound"')
    // 文本兜底必须是 v-else：写成并列的两个节点，真实标签页的 h1 会把标签名念两遍。
    expect(h1).toMatch(/<span\s+v-else>\{\{ tagName \}\}<\/span>/)
    expect(h1.match(/\{\{ tagName \}\}/g)?.length, 'h1 里标题文本只应出现一次').toBe(1)
  })
})
