/**
 * 单年归档路由契约（静态源码断言）。
 *
 * 这组端点（/blog/archive/{year}、/blog/archive/stats）此前长期"后端就绪、前端零消费"，
 * 本测试把接入方式钉住，防止后续改动把它重新变成不可达的死路由：
 *   1. /archive 页的年份标题必须链向 /archive/{year}——没有入口的路由等于没做；
 *   2. 年页只接受 4 位数字，非法参数在本页 404，不把垃圾值发给后端换 422；
 *   3. 日期渲染必须钉死时区（两端时区不一致会让 swr 缓存固化错版分组）；
 *   4. 新路由必须与 /archive 同档缓存，否则静默落回无缓存 SSR；
 *   5. 四语补齐文案键。
 */

import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const yearPagePath = resolve(ROOT, 'pages/archive/[year].vue')
const yearPage = readFileSync(yearPagePath, 'utf-8')
const archivePage = readFileSync(resolve(ROOT, 'pages/archive/index.vue'), 'utf-8')
const routeRules = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')
const NEW_KEYS = ['backToArchive', 'yearTitle', 'noYearPosts', 'statsTotal', 'statsYears']

describe('单年归档 /archive/[year]', () => {
  it('文件存在且请求按年归档端点', () => {
    expect(existsSync(yearPagePath)).toBe(true)
    // 父路由必须是目录式（archive.vue 与 archive/[year].vue 并存会让子路由
    // 静默渲染父组件、没有 outlet，表现为 /archive/2026 返回 200 却是 /archive 的内容）
    expect(existsSync(resolve(ROOT, 'pages/archive.vue'))).toBe(false)
    expect(yearPage).toContain('/blog/archive/${year}')
  })

  it('非法年份在发起请求前 404，不把垃圾参数发给后端', () => {
    const guardAt = yearPage.indexOf('createError')
    expect(guardAt).toBeGreaterThan(-1)
    expect(yearPage.slice(guardAt, guardAt + 90)).toContain('404')
    expect(guardAt).toBeLessThan(yearPage.indexOf('useAPI<'))
  })

  it('日期格式化钉死时区，避免服务端与访客分歧被 swr 固化', () => {
    expect(yearPage).toContain('Intl.DateTimeFormat')
    expect(yearPage).toContain('timeZone:')
    expect(yearPage).toContain('UTC')
  })

  it('/archive 页把年份标题做成链接，并给出归档统计读数', () => {
    expect(archivePage).toContain('`/archive/${group.year}`')
    expect(archivePage).toContain('/blog/archive/stats')
    expect(archivePage).toContain('archive.statsTotal')
  })

  it('新路由与 /archive 同档缓存', () => {
    const ruleAt = routeRules.indexOf('/archive/**')
    expect(ruleAt).toBeGreaterThan(-1)
    expect(routeRules.slice(ruleAt, ruleAt + 120)).toContain('swr: 3600')
  })

  it.each(['zh', 'en', 'ja', 'zh_Hant'] as const)('%s 具备归档页文案键', (locale) => {
    const messages = JSON.parse(
      readFileSync(resolve(ROOT, `i18n/locales/${locale}.json`), 'utf-8')
    ) as Record<string, Record<string, string>>
    for (const key of NEW_KEYS) {
      expect(messages.archive?.[key], `${locale} 缺 archive.${key}`).toBeTruthy()
    }
  })
})
