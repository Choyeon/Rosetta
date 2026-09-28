/**
 * 个人中心 /account 契约（静态源码断言）。
 *
 * 后端 GET /blog/users/me/{stats,posts,comments,likes,history} 与 DELETE 同路径自上线起
 * "就绪、前端零消费"（见 frontend/docs/API_COVERAGE.md），本测试把接入方式钉住：
 *   1. 六个端点都要有真实消费点，且父页写成目录式 pages/account/index.vue（§2.3.1）；
 *   2. 页面必须 SPA —— 内容逐登录用户不同，SSR 期没有 token，缓存也不能是公共 s-maxage；
 *      闸门写在命名中间件 auth-required，未登录带 redirect 跳 /login；
 *   3. 入口必须挂在顶栏用户菜单里（没有入口的路由等于没做）；
 *   4. 日期格式化钉死 locale + timeZone（本仓两端时区不一致过）；
 *   5. 四语补齐 account.* 文案键。
 */

import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const pagePath = resolve(ROOT, 'pages/account/index.vue')
const page = readFileSync(pagePath, 'utf-8')
const middleware = readFileSync(resolve(ROOT, 'middleware/auth-required.ts'), 'utf-8')
const header = readFileSync(resolve(ROOT, 'components/AppHeader.vue'), 'utf-8')
const config = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')

const NEW_KEYS = [
  'title', 'desc', 'statPosts', 'statComments', 'statLikes',
  'tabPosts', 'tabComments', 'tabLikes', 'tabHistory',
  'emptyPosts', 'emptyComments', 'emptyLikes', 'emptyHistory',
  'statusPublished', 'statusDraft', 'statusPending',
  'commentApproved', 'commentPending', 'deletedPost',
  'viewedAt', 'statsTotal', 'clearHistory', 'clearHistoryTitle',
  'clearHistoryBody', 'historyCleared', 'unlike', 'unliked',
  'loadFailed', 'retry', 'prevPage', 'nextPage'
]

describe('个人中心 /account', () => {
  it('文件存在且父页写成目录式（不阻塞未来子路由）', () => {
    expect(existsSync(pagePath)).toBe(true)
    // pages/account.vue 与 pages/account/index.vue 并存时，子路由会静默渲染无 outlet 的父组件
    expect(existsSync(resolve(ROOT, 'pages/account.vue'))).toBe(false)
  })

  it('六个 /users/me 端点都有真实消费点，写路径带二次确认', () => {
    // 列表四档共用一个响应式请求（url 随 tab 变），统计单独一档
    expect(page).toContain('`/blog/users/me/${tab.value}`')
    expect(page).toContain('/blog/users/me/stats')
    expect(page).toContain(`'/blog/users/me/history', { method: 'DELETE' }`)
    // 取消点赞复用后端 toggle，不在前端另造一套 DELETE 语义
    expect(page).toContain(`/blog/posts/\${id}/like`)
    // 清空是不可撤销写操作：确认对话框打开后才发请求
    expect(page).toContain('clearDialogOpen = true')
    expect(page).toContain('clearDialogOpen.value = false')
  })

  it('SPA 反选写在 routeRules 且缓存为 private，页面不重复声明第二套', () => {
    for (const path of ['/account', '/account/**']) {
      const at = config.indexOf(`'${path}': {`)
      expect(at, `routeRules 缺少 ${path}`).toBeGreaterThan(-1)
      const line = config.slice(at, config.indexOf('\n', at))
      expect(line).toContain('ssr: false')
      expect(line).toContain('no-store, private')
    }
    // 口径单源：页面里只允许出现解释性文字，不允许再写一份 ssr: false 元数据
    expect(page).not.toContain('ssr: false')
  })

  it('登录闸门在命名中间件，页面 setup 不做第二套状态判定', () => {
    expect(middleware).toContain('authStore.initialize()')
    expect(middleware).toContain('redirect=${encodeURIComponent(to.fullPath)}')
    const metaAt = page.indexOf('definePageMeta')
    expect(metaAt).toBeGreaterThan(-1)
    expect(page.slice(metaAt, metaAt + 90)).toContain('auth-required')
    // 全站中间件不得因此页扩容（个人中心是局部需求）
    expect(existsSync(resolve(ROOT, 'middleware/auth-required.global.ts'))).toBe(false)
  })

  it('顶栏用户菜单给出入口（桌面下拉 + 移动抽屉各一处）', () => {
    expect(header.match(/navigateTo\('\/account'\)/g)?.length).toBe(2)
  })

  it('日期格式化钉死时区，避免两端分歧', () => {
    expect(page).toContain('Intl.DateTimeFormat')
    expect(page).toContain('timeZone:')
    expect(page).toContain('UTC')
  })

  it.each(['zh', 'en', 'ja', 'zh_Hant'] as const)('%s 具备个人中心文案键', (locale) => {
    const messages = JSON.parse(
      readFileSync(resolve(ROOT, `i18n/locales/${locale}.json`), 'utf-8')
    ) as Record<string, Record<string, string>>
    for (const key of NEW_KEYS) {
      expect(messages.account?.[key], `${locale} 缺 account.${key}`).toBeTruthy()
    }
  })
})
