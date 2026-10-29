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
import { resolveNotificationText } from '../../lib/utils'

const LOCALES = ['zh', 'en', 'ja', 'zh_Hant']
const PAGE_REL = 'pages/account/notifications.vue'
const HEADER_REL = 'components/AppHeader.vue'
const ADMIN_HEADER_REL = 'components/admin/AdminHeader.vue'

const pagePath = resolve(process.cwd(), PAGE_REL)
const page = existsSync(pagePath) ? readFileSync(pagePath, 'utf8') : ''
const header = readFileSync(resolve(process.cwd(), HEADER_REL), 'utf8')
const adminHeader = readFileSync(resolve(process.cwd(), ADMIN_HEADER_REL), 'utf8')
const dicts = Object.fromEntries(
  LOCALES.map(loc => [loc, JSON.parse(readFileSync(resolve(process.cwd(), `i18n/locales/${loc}.json`), 'utf8')) as Record<string, unknown>])
)

describe('站内通知 · 前台落地契约', () => {
  it('通知页存在且真的消费四条读/写接口', () => {
    expect(existsSync(pagePath), `缺少 ${PAGE_REL}`).toBe(true)
    for (const fn of ['fetchNotifications', 'markNotificationRead', 'markAllNotificationsRead', 'deleteNotification', 'clearAllNotifications']) {
      expect(page, `通知页必须调用 ${fn}`).toContain(`${fn}(`)
    }
  })

  it('清空只针对已读，且必须过二次确认', () => {
    // 未读是"还没看过的回执"：一键抹掉等于替用户做决定，所以写死 read_only: true
    expect(page).toContain('clearAllNotifications({ read_only: true }')
    expect(page).toContain('confirmClearOpen = true')
    expect(page).toContain('AlertDialogAction')
    // 已读数只能由未筛选的全量读数算出（筛选态下 total 是子集）
    expect(page).toMatch(/if \(!unreadOnly\.value\) hasRead\.value = \(res\.total - res\.unread_count\) > 0/)
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
    // 只查真实指令绑定：文件头注释里写"绝不 v-html"不算违规
    expect(page, 'v-html 会把留言摘要当标记渲染').not.toMatch(/v-html\s*=/)
    expect(page).toMatch(/\{\{ resolveNotificationText\(row\.title, locale\) \}\}/)
    expect(page).toMatch(/\{\{ resolveNotificationText\(row\.message, locale\) \}\}/)
  })

  it('标题/正文两种历史形态都过解析层，不把 dict toString 成 JSON 上屏', () => {
    // 后端 NotificationItemOut.title/message 是 `dict | str`：系统通知是四语 dict，
    // UGC 通知是明文字符串。直接插值会把 dict 原样渲染成 {"zh":…}（线上实测可见）。
    expect(page, '原始插值等于把 dict 当字符串输出').not.toMatch(/\{\{ row\.(title|message) \}\}/)
    expect(page).toContain('resolveNotificationText')
    expect(adminHeader).toContain('resolveNotificationText')

    const dict = { zh: '评论通知', en: 'Comment', ja: 'コメント', zh_Hant: '評論' }
    expect(resolveNotificationText(dict, 'en')).toBe('Comment')
    expect(resolveNotificationText(dict, 'zh_Hant')).toBe('評論')
    // 语言缺失时按 zh → en → ja → zh_Hant 兜底，绝不返回 JSON 文本
    expect(resolveNotificationText({ zh: '仅中文' }, 'ja')).toBe('仅中文')
    // UGC 明文字符串原样透传（刻意不自动翻译）
    expect(resolveNotificationText('你的文章收到新评论', 'en')).toBe('你的文章收到新评论')
    expect(resolveNotificationText(null, 'zh')).toBe('')
    expect(resolveNotificationText({}, 'zh')).toBe('')
  })

  it('顶栏两处入口（桌面下拉 + 移动抽屉）都指向通知页', () => {
    const hits = [...header.matchAll(/go\('\/account\/notifications'\)/g)]
    expect(hits.length, '桌面与移动各一处').toBeGreaterThanOrEqual(2)
  })

  it('页面用到的 notifications.* i18n key 在四语齐全', () => {
    const keys = [...page.matchAll(/t\('notifications\.([A-Za-z0-9_]+)'/g)].map(m => m[1] ?? '')
    expect(keys.length, '页面必须用到 notifications 命名空间').toBeGreaterThan(5)
    const missing: string[] = []
    for (const loc of LOCALES) {
      const ns = dicts[loc]?.notifications as Record<string, unknown> | undefined
      for (const key of new Set(keys)) {
        if (!ns || typeof ns[key] !== 'string' || ns[key] === '') missing.push(`${loc}: notifications.${key}`)
      }
    }
    expect(missing, `缺翻译：${missing.join(', ')}`).toEqual([])
  })
})
