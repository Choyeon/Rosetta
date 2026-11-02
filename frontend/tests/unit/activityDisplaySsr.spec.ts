/**
 * 动态时间线的显示面契约。
 *
 * 这一页是 swr 600 的公开 SSR 页，所以下面四条判据同时是 SEO 判据与 hydration 判据：
 *   ① 作者名必须是真实 `<a href>`（走 `localeHref("/authors/<handle>")`）——做成 `<span>`
 *      时作者页在链接图里只剩首页热门作者那一处，爬虫从动态流读不到这条边；
 *   ② 缺 `created_at` 时留空串，不得回落到 `new Date()`：那个兜底值服务器与浏览器各算
 *      一次，首渲染字节就不一致（同族缺陷在文章页是批次 #132 收的）；
 *   ③ 长动态折叠的判据只吃正文字符数与换行数——纯字符串函数，SSR 首屏即折叠态；判据里
 *      时间或 DOM 就两端分叉；
 *   ④「按类型筛完是空的」与「全站没有动态」是两件事，前者必须给一条真实 `<a href>` 出口，
 *      否则访客停在死胡同、筛选组合也失去回退边。
 *
 * 本仓 typecheck/vitest 在开发机上跑不了（无 node），故每条判据另有
 * `scripts_tmp/verify_activity_display_spec.py` 的等价 python 实现。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/activity.vue'), 'utf-8').replace(/\r\n/g, '\n')
// 根 `<template>` 之后还有三层插槽用的 `</template>`，切到 `<script>` 才覆盖整段模板
const template = src.slice(0, src.indexOf('<script'))
// 注释里提 `new Date()` 是解释「为什么不能这么兜底」，所以只查代码行
const codeLines = src.split('\n').filter(line => !/^\s*(\/\/|\*|<!--)/.test(line))

const activityOf = (data: Record<string, unknown>): Record<string, string> =>
  (data.activity ?? {}) as Record<string, string>

const locales = ['zh', 'en', 'ja', 'zh_Hant'].map(code => ({
  code,
  data: JSON.parse(
    readFileSync(resolve(ROOT, `i18n/locales/${code}.json`), 'utf-8')
  ) as Record<string, unknown>
}))

describe('动态流的作者名是真实锚点', () => {
  it('头像壳按 author_url 在 a/span 间切换，且带显式 href', () => {
    expect(template).toContain(':is="item.author_url ? \'a\' : \'span\'"')
    expect(template).toContain(':href="item.author_url || undefined"')
  })

  it('author_url 由 localeHref 单源产生并对 handle 做 URL 编码', () => {
    expect(src).toContain('const { localeHref } = useLocaleLink()')
    expect(src).toContain('localeHref(`/authors/${encodeURIComponent(authorHandle)}`)')
  })

  it('行数据声明 author_url，缺 handle 时是空串', () => {
    expect(src).toContain('author_url?: string')
    expect(src).toContain('typeof author.username === \'string\' ? author.username.trim() : \'\'')
  })
})

describe('created_at 兜底不得含时间', () => {
  it('代码行里不再出现 new Date(', () => {
    expect(codeLines.filter(line => line.includes('new Date('))).toEqual([])
  })

  it('缺 created_at 时留空串，模板侧用 v-if 守卫', () => {
    expect(src).toMatch(/created_at:\s*\(typeof r\.created_at === 'string' && r\.created_at\) \|\| ''/)
    expect(template).toContain('v-if="item.created_at"')
  })
})

describe('长动态折叠：判据必须是纯字符串函数', () => {
  it('判据只吃字符数与换行数，并给出两个阈值常量', () => {
    expect(src).toContain('const CLAMP_CHARS = 160')
    expect(src).toContain('const CLAMP_LINES = 5')
    expect(src).toContain('content.length > CLAMP_CHARS')
    expect(src).toContain('content.match(/\\n/g)?.length ?? 0')
    expect(src).toContain('>= CLAMP_LINES')
  })

  it('展开态存在不可变 Set 里，切换时换新集合', () => {
    expect(src).toContain('const expandedActivityIds = ref<Set<number>>(new Set())')
    expect(src).toContain('const next = new Set(expandedActivityIds.value)')
    expect(src).toContain('expandedActivityIds.value = next')
  })

  it('折叠类只在「够长且未展开」时给出，模板两端共用同一判据', () => {
    expect(src).toContain('isLongActivity(item.content) && !isExpandedActivity(item.id) ? \'line-clamp-6\' : \'\'')
    expect(template).toContain(':class="isExpandedActivity(item.id) ? \'\' : activityClampClass(item)"')
    expect(template).toContain('v-if="isLongActivity(item.content)"')
    expect(template).toContain(':aria-expanded=')
  })
})

describe('按类型筛空不等于没有动态', () => {
  it('空态文案按 currentType 二选一', () => {
    expect(template).toContain('currentType ? t(\'activity.emptyFiltered\') : t(\'activity.noActivity\')')
  })

  it('带筛选时出口是真实 <a href>，指向 typeHref(null)', () => {
    const exitAt = template.indexOf(':href="typeHref(null)"')
    expect(exitAt).toBeGreaterThan(-1)
    const exitBlock = template.slice(exitAt - 400, exitAt + 400)
    expect(exitBlock).toContain('<a')
    expect(exitBlock).toContain('t(\'activity.viewAll\')')
    expect(exitBlock).toContain('@click.prevent')
    expect(exitBlock).toContain('v-if="currentType"')
  })

  it('四语补齐新增四键，退役四键不得回潮', () => {
    for (const entry of locales) {
      const activity = activityOf(entry.data)
      for (const key of ['emptyFiltered', 'viewAll', 'expand', 'collapse']) {
        expect(activity[key], `${entry.code}: activity.${key} 缺失`).toBeTruthy()
      }
      for (const dead of ['type_card', 'type_comment', 'type_like', 'type_post']) {
        expect(activity, `${entry.code} 仍带死键 activity.${dead}`).not.toHaveProperty(dead)
      }
    }
  })
})
