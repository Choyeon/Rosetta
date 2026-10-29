/**
 * 文章详情页的 404 口径（静态源码断言）。
 *
 * 踩过的坑：不存在的文章 slug 返回的是 HTTP 404（`useContentStatus` 改的状态码），
 * 但模板仍然把整页文章壳渲染出来——面包屑下面跟着 Anonymous 作者行、
 * 「1 分钟阅读 / 0 阅读」、点赞/收藏/分享按钮、投票卡、评论框（0/3000）、
 * 相关文章与目录侧栏。等于给一个不存在的 URL 配了整套可交互界面，
 * 访客看到的是"打开了一篇空文章"，而不是"这篇不存在"。
 *
 * 修法口径（三条，改回任一条都会复现）：
 *   1) 404 只渲染一块「页面不存在」面板，且**不放进 ClientOnly**——404 在 SSR
 *      期就已确定，不执行 JS 的抓取器也要读到这段文案；
 *   2) 文章壳（作者行/互动行/投票/评论/相关文章）整段收在 `<template v-else>` 里，
 *      不再是"面板盖在文章壳上"；
 *   3) 目录/阅读时长侧栏与顶部阅读进度条这类"正在读本文"的信号同口径收掉。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const src = readFileSync(resolve(__dirname, '..', '..', 'pages/posts/[slug].vue'), 'utf-8')

/** 从 `<template v-else>` 开标签起按标签配对找到块尾（内部还有 <template #fallback> 等嵌套）。 */
function vElseBlockRange(source: string): [number, number] {
  const start = source.search(/<template\s+v-else\s*>/)
  if (start < 0) throw new Error('找不到 <template v-else>')
  const re = /<template\b|<\/template>/g
  re.lastIndex = start
  let depth = 0
  for (let m = re.exec(source); m; m = re.exec(source)) {
    depth += m[0].startsWith('</') ? -1 : 1
    if (depth === 0) return [start, m.index]
  }
  throw new Error('<template v-else> 未闭合')
}

describe('文章详情页 404', () => {
  it('404 面板在 SSR 里就能渲染，且给出返回列表 / 返回首页两条出口', () => {
    const panel = src.slice(src.search(/<div\s+v-if="postNotFound"/), src.search(/<template\s+v-else\s*>/))
    expect(panel.length, '必须存在以 postNotFound 为条件的 404 面板').toBeGreaterThan(0)
    expect(panel, '404 面板不得关进 ClientOnly：SSR 产物里要读得到这段话').not.toContain('ClientOnly')
    expect(panel).toContain('error.notFoundDesc')
    // 标题只出现一次：面包屑与 h1 已经写着「页面不存在」，面板里再放一个同样的标题
    // 就是同一句话第三次出现（线上实测三连重复）。
    expect(panel).not.toContain('error.notFoundTitle')
    expect(panel).toContain('post.backToList')
    expect(panel).toContain('error.backHome')
  })

  it('文章壳整体收在 v-else 里：互动行 / 投票 / 评论 / 相关文章一条都不能漏在外面', () => {
    const [start, end] = vElseBlockRange(src)
    const shell = src.slice(start, end)
    expect(shell.length).toBeGreaterThan(0)
    // 这四块是 404 页面上最刺眼的部分：给不存在的文章点赞、投票、评论、看推荐。
    for (const marker of ['showLikeButton', 'PollCard', 'showCommentsSection', 'showRelatedPosts']) {
      expect(shell, `文章壳区段里应当包含 ${marker}`).toContain(marker)
    }
    // 反过来：面板与壳之间不能再出现一份"Anonymous / 0 阅读"这类作者元信息行。
    const head = src.slice(0, start)
    expect(head).not.toContain('showReadingTime')
  })

  it('目录侧栏与阅读进度条同口径：404 时不显示', () => {
    expect(src).toMatch(/const showAside = computed\(\s*\(\) => !postNotFound\.value &&/)
    expect(src).toMatch(/const showReadingProgress = computed\(\s*\(\) => !postNotFound\.value &&/)
  })
})
