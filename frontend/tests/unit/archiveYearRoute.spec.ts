/**
 * 单年归档路由契约（静态源码断言）。
 *
 * 这组端点（/blog/archive/{year}、/blog/archive/stats）此前长期"后端就绪、前端零消费"，
 * 本测试把接入方式钉住，防止后续改动把它重新变成不可达的死路由：
 *   1. /archive 页的年份标题必须链向 /archive/{year}——没有入口的路由等于没做；
 *   2. 年页只接受 4 位数字，非法参数由命名路由中间件 abort（页面 setup 里 throw 仍是 HTTP 200）；
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

  it('非法年份由路由中间件在服务端 abort，页面 setup 不自己 throw', () => {
    // 页面 setup 里 throw createError 会渲染 error.vue，但响应仍是 HTTP 200，
    // 且被 /archive/** 的 swr 缓存固化成一个可复用的 200 页——闸门必须在中间件。
    const middlewarePath = resolve(ROOT, 'middleware/archive-year.ts')
    expect(existsSync(middlewarePath)).toBe(true)
    const middleware = readFileSync(middlewarePath, 'utf-8')
    expect(middleware).toContain('abortNavigation')
    expect(middleware).toContain('statusCode: 404')
    expect(middleware).toContain('d{4}')
    // 挂在与文件名，不进全局链
    const metaAt = yearPage.indexOf('definePageMeta')
    expect(metaAt).toBeGreaterThan(-1)
    expect(yearPage.slice(metaAt, metaAt + 80)).toContain('archive-year')
    // 页面侧只留纯解析，不再有第二套闸门
    expect(yearPage).not.toContain('createError')
    expect(yearPage).toContain('Number(route.params.year)')
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
