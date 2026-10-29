/**
 * 归档两级落地页（/archive/<year>、/archive/<year>/<month>）的口径（静态源码断言）。
 *
 * 踩过的坑（线上实测 2026-10-29）：`/archive/1999` 返回 HTTP 404（`useContentStatus` 改的
 * 状态码），页面却照常渲染「1999 年归档 / 共 0 篇文章 / 该年份暂无已发布文章」——
 * 面包屑下面是一份"确实存在的空年份页"，而不是"这个 URL 不存在"。月份页同型
 * （`/archive/2026/07`）。反过来，接口 5xx 时页面说的是「该年份暂无已发布文章」，
 * 把一次临时故障说成了内容状态。
 *
 * 修法口径（四条，改回任一条都会复现）：
 *   1) 不存在分支是 `v-if`/`v-else` 的**外层**开关，页头（h1 + 「共 N 篇文章」）整段
 *      收进 `v-else`——0 篇是对"存在但这年没发文章"的描述，404 页不该有这句；
 *   2) 面板给文案，外加两条出口（返回上一级归档 / 返回首页），不得复用「加载失败」文案；
 *   3) 加载中不算缺失：`yearNotFound` / `monthNotFound` 必须带 pending 守卫，否则
 *      每个真实年份/月份会先闪一次 404 面板；
 *   4) 请求失败有独立分支，不能落进"暂无文章"。
 *
 * 另一半是同一批修的时区口径：后端归档边界已统一到 UTC（repositories/post.py 的
 * utc_*），前端的年份分组与「月日」展示也必须是 UTC，否则服务端（Asia/Shanghai）与
 * 访客在跨年/跨日那几小时分到不同组，带 swr 的页面还会把服务端那份固化进缓存。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const read = (file: string) => readFileSync(resolve(ROOT, file), 'utf-8')

interface Case {
  file: string
  flag: string
  backPathSnip: string
}

const cases: Case[] = [
  { file: 'pages/archive/[year]/index.vue', flag: 'yearNotFound', backPathSnip: 'localeHref(\'/archive\')' },
  { file: 'pages/archive/[year]/[month].vue', flag: 'monthNotFound', backPathSnip: 'localeHref(`/archive/${year}`)' }
]

describe.each(cases)('$file 的 404 口径', ({ file, flag, backPathSnip }) => {
  const src = read(file)

  it('不存在分支是外层开关，且排在加载 / 失败分支之前', () => {
    const notFound = src.search(new RegExp(`<template\\s+v-if="${flag}"`))
    const loadError = src.search(/v-else-if="(?:groupsError|error)"/)
    expect(notFound, `缺少 ${flag} 分支`).toBeGreaterThan(0)
    expect(loadError).toBeGreaterThan(0)
    expect(notFound).toBeLessThan(loadError)
  })

  it('不存在面板给文案与两条出口，不冒充加载失败', () => {
    const start = src.search(new RegExp(`<template\\s+v-if="${flag}"`))
    const end = src.indexOf('</template>', start)
    const panel = src.slice(start, end)
    expect(panel).toContain('error.notFoundDesc')
    expect(panel).toContain(backPathSnip)
    expect(panel).toContain('error.backHome')
    expect(panel).not.toContain('error.loadFailed')
  })

  it('页头（h1 + 文章总数）只在存在分支里渲染', () => {
    const elseStart = src.search(/<template\s+v-else>/)
    const headerStart = src.indexOf('<header')
    expect(elseStart, '缺少 v-else 分支').toBeGreaterThan(0)
    expect(headerStart).toBeGreaterThan(elseStart)
    const header = src.slice(headerStart, src.indexOf('</header>', headerStart))
    expect(header).toContain('archive.statsTotal')
  })

  it('加载中不算缺失：判定带 pending 守卫', () => {
    expect(src).toMatch(new RegExp(`const ${flag} = computed\\(\\s*\\(\\) =>\\s*!(?:_pending|pending)\\.value && isContentMissing`))
  })

  it('请求失败有独立分支', () => {
    expect(src).toMatch(/v-else-if="(?:groupsError|error)"/)
    expect(src).toContain('error.serverErrorDesc')
  })
})

describe('归档的时区口径（UTC）', () => {
  it('/archive 的年份分组用 getUTCFullYear，不用本地 getFullYear', () => {
    const src = read('pages/archive/index.vue')
    expect(src).toContain('getUTCFullYear()')
    expect(src, '分组一换回本地时区，跨年文章就会与服务端缓存/年份落地页错开').not.toMatch(/\.getFullYear\(\)/)
  })

  it('「月日」形态取 UTC 分量（与后端归档分组同源）', () => {
    const src = read('composables/useI18nHelpers.ts')
    const start = src.indexOf('export function formatMonthDayText')
    const end = src.indexOf('\n}', start)
    const body = src.slice(start, end)
    expect(body).toContain('getUTCDate()')
    expect(body).toContain('monthNameOf(localeCode, d, true)')
    expect(body).not.toContain('d.getDate()')
  })
})
