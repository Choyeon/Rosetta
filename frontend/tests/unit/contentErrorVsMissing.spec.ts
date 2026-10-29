/**
 * 「不存在」与「暂时读不到」必须分成两条分支（静态源码断言）。
 *
 * 踩过的坑：页面用 `loadError = !!error || !data` 当闸门，把 5xx / 断网与真 404 混成一个
 * 视图——后端抖一下，一个真实存在的页面（独立页 `/about`、兼容页 `/page/about`、
 * 系列页）就被渲染成「页面不存在」，独立页还会因为 isContentMissing 判不出 5xx 而
 * 连 HTTP 状态码一起写成 404（搜索引擎当永久删除）。
 *
 * 三条口径（三个页面同源）：
 *   1) 404 分支只由 isContentMissing 驱动，不再叠 `!!error`；
 *   2) 请求失败有独立分支，给可重试按钮，不出现「不存在」文案；
 *   3) 顶层 catchall 的取数 handler 不得把所有异常都吞成 null（那样 error 永远是空，
 *      5xx 与 404 在页面上无从区分）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const read = (file: string) => readFileSync(resolve(ROOT, file), 'utf-8')

const cases = [
  // 顶层 catchall 把失败形态记在 loadFailure（不能在页面里 throw createError，见 contentNotFoundStatus）
  { file: 'pages/[slug].vue', flag: 'pageNotFound', failFlag: 'loadFailure', retry: 'retryLoad()' },
  { file: 'pages/page/[slug].vue', flag: 'compatPageNotFound', failFlag: 'error', retry: 'refresh()' },
  { file: 'pages/series/[slug].vue', flag: 'seriesNotFound', failFlag: 'error', retry: 'refresh()' }
]

describe.each(cases)('$file 的失败口径', ({ file, flag, failFlag, retry }) => {
  const src = read(file)

  it('不存在分支由 isContentMissing 驱动，且排在失败分支之前', () => {
    const notFound = src.search(new RegExp(`v-else-if="${flag}"`))
    const loadError = src.search(new RegExp(`v-else-if="${failFlag}"`))
    expect(notFound, `缺少 ${flag} 分支`).toBeGreaterThan(0)
    expect(loadError, '缺少独立的请求失败分支').toBeGreaterThan(0)
    expect(notFound).toBeLessThan(loadError)
    expect(src).toMatch(new RegExp(`const ${flag} = computed\\(\\(\\) => isContentMissing\\(`))
  })

  it('失败分支可重试，且不说「不存在」', () => {
    const start = src.search(new RegExp(`v-else-if="${failFlag}"`))
    const block = src.slice(start, src.indexOf('</div>', start))
    expect(block).toContain('error.serverErrorDesc')
    expect(block).toContain(retry)
    expect(block).not.toContain('notFoundTitle')
  })

  it('旧的 `!!error || !data` 闸门已删除（它与 404 判定互相打脸）', () => {
    expect(src).not.toMatch(/const loadError = computed\(\(\) => !!error\.value/)
    expect(src).not.toMatch(/v-else-if="loadError/)
  })
})

describe('顶层 catchall 不再把 5xx 吞成「不存在」', () => {
  const src = read('pages/[slug].vue')

  it('取数 handler 记下主请求状态码，非 404 时进失败分支而不是当缺失', () => {
    expect(src).toContain('primaryStatus')
    expect(src).toMatch(/if \(primaryStatus !== 404\) loadFailure\.value = primaryStatus \|\| 503/)
    // 缺失判定必须排除失败态，否则 5xx 会被 isContentMissing 判成 404
    expect(src).toMatch(/const pageMissing = computed\(\(\) => !page\.value && !redirectedAway\.value && !loadFailure\.value\)/)
    expect(src).not.toMatch(/throw\s+createError\(/)
  })
})
