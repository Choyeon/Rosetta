/**
 * 系列详情页的三条分支口径（静态源码断言）。
 *
 * 踩过的坑：模板曾写 `v-else-if="notFound || !series"`，而 `notFound = !!error || missing`——
 * 任何一次网络故障 / 5xx 都会显示成「系列不存在 / 该系列可能尚未发布或已被移除」，
 * 访客以为系列被删了（实际刷新就能回来）。状态码那一侧由 useContentStatus 判得很准，
 * 页面文案却跟着 `!!error` 走，两处口径互相打脸。
 *
 * 四条口径：
 *   1) 不存在分支必须由 `seriesNotFound`（isContentMissing）驱动，不得再叠 `!!error`；
 *   2) 请求失败有独立分支，给可重试的错误文案，不得出现「系列不存在」；
 *   3) 不存在面板给两条真链接（返回系列列表 / 返回首页），按钮不能只挂 @click
 *      （爬虫读不到 href，键盘与中键也打不开）；
 *   4) 数据必须 SSR 取数：`server: false` 会让服务端恒为 null，SSR 输出骨架、useSeo 拿不到系列名。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const src = readFileSync(resolve(__dirname, '..', '..', 'pages/series/[slug].vue'), 'utf-8')

describe('系列详情页的 404 / 失败口径', () => {
  it('不存在分支由 isContentMissing 驱动，且排在失败分支之前', () => {
    const notFound = src.search(/<template\s+v-else-if="seriesNotFound"/)
    const loadError = src.search(/<div\s+v-else-if="error"/)
    expect(notFound, '缺少 seriesNotFound 分支').toBeGreaterThan(0)
    expect(loadError, '缺少独立的请求失败分支').toBeGreaterThan(0)
    expect(notFound).toBeLessThan(loadError)
  })

  it('不存在面板给两条真链接，不冒充加载失败', () => {
    const start = src.search(/<template\s+v-else-if="seriesNotFound"/)
    const panel = src.slice(start, src.indexOf('</template>', start))
    expect(panel).toContain(`localeHref('/series')`)
    expect(panel).toContain(`localeHref('/')`)
    expect(panel).toContain('series.notFoundTitle')
    expect(panel).not.toMatch(/@click="navigateTo/)
    expect(panel).not.toContain('error.serverErrorDesc')
  })

  it('请求失败分支可重试，且不说「不存在」', () => {
    const start = src.search(/<div\s+v-else-if="error"/)
    const block = src.slice(start, src.indexOf('</div>', start))
    expect(block).toContain('error.serverErrorDesc')
    expect(block).toContain('refresh()')
    expect(block).not.toContain('series.notFoundTitle')
  })

  it('失败不再被当成不存在：notFound 那条 `!!error` 判定已删除', () => {
    expect(src).not.toMatch(/const notFound = computed\(\(\) => !!error\.value/)
    expect(src).toMatch(/const seriesNotFound = computed\(\(\) => isContentMissing\(/)
  })

  it('数据走 SSR 取数（server:false 会让服务端恒为 null，SSR 吐骨架）', () => {
    // 注释里会提到"曾经写过 server: false"，只扫真代码行
    const code = src
      .replace(/<!--[\s\S]*?-->/g, '')
      .split('\n')
      .filter(line => !line.trim().startsWith('//'))
      .join('\n')
    expect(code).not.toMatch(/server:\s*false/)
  })
})
