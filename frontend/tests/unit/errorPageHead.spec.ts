/**
 * 根级兜底页（error.vue）的 <head> 契约。
 *
 * error.vue 不经过 useSeo，也不在 pages/ 下——没人替它写 robots / description。
 * 实测（生产，`GET /a/b/c/d` + `Accept: text/html`）：
 *   - <title>404 · 页面不存在 · Rosetta</title>   ← 品牌名写死成内部项目名，
 *     而站内每一页都是「… · Choyeon Blog」，运营者改站名后唯独兜底页不跟；
 *   - 没有任何 <meta name="robots">；
 *   - description 还是 nuxt.config 那条产品介绍（"Modern personal blog system with
 *     Nuxt 4 + FastAPI"），与「页面不存在」互相矛盾。
 *
 * 三条都用静态源码断言钉住，口径与 AGENTS §2.3.3.4（robots 只允许 NOINDEX_ROBOTS 单源）一致。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'error.vue'), 'utf-8')

describe('error.vue 的 head 单源', () => {
  it('标题后缀读站点名，不再写死项目名', () => {
    expect(src).toContain('useSite()')
    expect(src).toMatch(/site\?\.siteTitle\.value/)
    // 正面钉住唯一形态：模板串里只有 statusCode + titleWithSuffix，末尾不再挂品牌字面量
    expect(src).toMatch(
      /title: computed\(\(\) => `\$\{statusCode\.value\} · \$\{titleWithSuffix\(pageTitle\.value\)\}`\)/
    )
  })

  it('robots 走 NOINDEX_ROBOTS 单源常量（不是手写字符串）', () => {
    expect(src).toMatch(/import \{ NOINDEX_ROBOTS \} from '~~\/composables\/useSeo'/)
    expect(src).toMatch(/name: 'robots', content: NOINDEX_ROBOTS/)
    // 手写 "noindex, nofollow" 会一边允许抓取一边掐断内链，全仓只允许一个写法
    expect(src).not.toContain('noindex, nofollow')
  })

  it('description 用本页文案，不再继承 nuxt.config 的产品介绍', () => {
    expect(src).toMatch(/name: 'description', content: computed\(\(\) => pageDesc\.value\)/)
  })
})
