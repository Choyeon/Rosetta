/**
 * 内容不存在时的真实 HTTP 状态码契约（静态源码断言）。
 *
 * 实测（生产构建 + 独立实例）：/posts、/categories、/tags、/page 四类动态详情页对
 * 不存在的 slug 全部返回 HTTP 200 的兜底 UI——后端这些路径明确回 404，前端把状态码
 * 吞掉了。WordPress 口径下"不存在的内容"必须是 404，否则爬虫会把空壳收进索引，
 * 而且这些路由带 swr，200 会被缓存成可复用的"正常页"。
 *
 * 本测试钉住四页都接了 useContentStatus，且没有改用页面内 throw createError
 * （那条路径渲染 error.vue 但响应仍是 200，见 AGENTS §2.3.2）。
 */

import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const helperPath = resolve(ROOT, 'composables/useContentStatus.ts')
const helper = readFileSync(helperPath, 'utf-8')

const PAGES = [
  'pages/posts/[slug].vue',
  'pages/categories/[slug].vue',
  'pages/tags/[slug].vue',
  'pages/page/[slug].vue'
]

describe('内容页 404 状态码闸门', () => {
  it('helper 只在服务端改状态码，且只认明确 404 / 成功但空对象', () => {
    expect(existsSync(helperPath)).toBe(true)
    // 注意：needle 不能写成完整的 'import.meta.server' —— vitest 会把这个字面量
    // 当作 define 目标替换成 false，断言就变成了 toContain(false)。
    expect(helper).toContain('import.meta')
    expect(helper).toContain('server) return')
    expect(helper).toContain('useRequestEvent')
    expect(helper).toContain('setResponseStatus')
    // 判定时点必须是 app:rendered：setup 同步期 useFetch payload 还没落值，
    // 在那里读 missing 会把真实页面一起判成 404（第一版就是这么错的）。
    expect(helper).toContain('app:rendered')
    expect(helper).toContain('status === 404')
    // 故障与 5xx 不得被写成 404（临时故障判成永久删除会掉索引）
    expect(helper).toContain('err == null && missing.value')
  })

  it.each(PAGES)('%s 接线 helper，且不用页面内 createError 冒充 404', (rel) => {
    const src = readFileSync(resolve(ROOT, rel), 'utf-8')
    expect(src).toContain('useContentStatus')
    expect(src).toContain('composables/useContentStatus')
    expect(src).not.toContain('createError')
  })

  it.each(PAGES)('%s 缺内容时标题走 404 文案，不再伪造 slug 标题', (rel) => {
    const src = readFileSync(resolve(ROOT, rel), 'utf-8')
    expect(src).toContain('error.notFoundTitle')
    // 旧口径是 `pickLocalized(...) || slug.value || ''`：404 页的 <title> 变成一串
    // 假装是分类名的乱码。WordPress 的 404 标题就是"页面不存在"。
    expect(src).not.toMatch(/\|\|\s*slug\.value \|\| ''/)
  })

  it('四语都有 error.notFoundTitle 文案', () => {
    for (const loc of ['zh', 'en', 'ja', 'zh_Hant']) {
      const messages = JSON.parse(
        readFileSync(resolve(ROOT, `i18n/locales/${loc}.json`), 'utf-8')
      ) as Record<string, Record<string, string>>
      expect(messages.error?.notFoundTitle, `${loc} 缺 error.notFoundTitle`).toBeTruthy()
    }
  })
})
