/**
 * 站内通知的前台落地契约。
 *
 * 起因：`/api/notifications` 八条端点的鉴权门槛是 CurrentUser（任何登录用户），
 * 普通成员本来就会收到"评论已通过""有人回复你"这类回执，但落地 UI 只有后台
 * AdminHeader 的通知面板——非管理员登录后没有任何入口能读到自己的通知。
 * 这一类缺口的表现不是报错，而是"功能看起来不存在"，所以钉成门禁。
 *
 * 另外顺手把「页面用到的 i18n key 必须在四语里都存在」收进来：缺语言不会构建失败，
 * 只会在界面上露出裸 key，等于把一个语言版本的用户界面弄坏。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const LOCALES = ['zh', 'en', 'ja', 'zh_Hant']
const PAGE_REL = 'pages/account/notifications.vue'
const HEADER_REL = 'components/AppHeader.vue'

const pagePath = resolve(process.cwd(), PAGE_REL)
const page = existsSync(pagePath) ? readFileSync(pagePath, 'utf8') : ''
const header = readFileSync(resolve(process.cwd(), HEADER_REL), 'utf8')
const dicts = Object.fromEntries(
  LOCALES.map(loc => [loc, JSON.parse(readFileSync(resolve(process.cwd(), `i18n/locales/${loc}.json`), 'utf8')) as Record<string, unknown>])
)

describe('站内通知 · 前台落地契约', () => {
  it('通知页存在且真的消费四条读/写接口', () => {
    expect(existsSync(pagePath), `缺少 ${PAGE_REL}`).toBe(true)
    for (const fn of ['fetchNotifications', 'markNotificationRead', 'markAllNotificationsRead', 'deleteNotification']) {
      expect(page, `通知页必须调用 ${fn}`).toContain(`${fn}(`)
    }
  })

  it('通知页是登录态私有页（ssr 档位由 /account/** routeRules 反选）', () => {
    expect(page).toMatch(/middleware: 'auth-required'/)
    expect(page, '页面不应重复声明 ssr：档位由 nuxt.config 的 /account/** 单源负责')
      .not.toMatch(/ssr:\s*false/)
  })

  it('读取失败显示错误态并给重试，不得伪装成"暂无通知"', () => {
    expect(page).toMatch(/loadError/)
    expect(page, '空态与错误态必须是两个分支').toMatch(/notifications\.empty/)
    expect(page).toMatch(/notifications\.loadFailed/)
    expect(page).toMatch(/common\.retry/)
  })

  it('通知标题/正文来自 UGC，只能文本插值', () => {
    expect(page, 'v-html 会把留言摘要当标记渲染').not.toMatch(/v-html/)
    expect(page).toMatch(/\{\{ row\.title \}\}/)
    expect(page).toMatch(/\{\{ row\.message \}\}/)
  })

  it('顶栏两处入口（桌面下拉 + 移动抽屉）都指向通知页', () => {
    const hits = [...header.matchAll(/navigateTo\('\/account\/notifications'\)/g)]
    expect(hits.length, '桌面与移动各一处').toBeGreaterThanOrEqual(2)
  })

  it('页面用到的 notifications.* i18n key 在四语齐全', () => {
    const keys = [...page.matchAll(/t\('notifications\.([A-Za-z0-9_]+)'/g)].map(m => m[1] ?? '')
    expect(keys.length, '页面必须用到 notifications 命名空间').toBeGreaterThan(5)
    const missing: string[] = []
    for (const loc of LOCALES) {
      const ns = dicts[loc].notifications as Record<string, unknown> | undefined
      for (const key of new Set(keys)) {
        if (!ns || typeof ns[key] !== 'string' || ns[key] === '') missing.push(`${loc}: notifications.${key}`)
      }
    }
    expect(missing, `缺翻译：${missing.join(', ')}`).toEqual([])
  })
})
