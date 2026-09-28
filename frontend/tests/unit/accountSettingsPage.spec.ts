/**
 * 账户设置 /account/settings 契约（静态源码断言）。
 *
 * 这一页把 users 模块里最后三个"后端就绪、前端零消费"的自服务写端点接上：
 * PUT /users/me、PUT /users/me/preferences、POST /users/me/password
 * （GET /users/me/preferences 由 useAPI 消费）。钉住的口径：
 *   1. 写请求全部走 apiFetch（统一失败信封 + toast），取数据走 useAPI；
 *   2. 隐私开关只暴露**后端真有强制点**的 5 个字段。UserPreference.theme 是死字段
 *      （models/user.py 里唯一引用是 __repr__），放开关等于给用户一个不生效的设置；
 *   3. 改密成功必须 clearTokens + 跳 /login：后端 bump token_version 让全部会话失效，
 *      留在原页只会让下一个请求撞 401 自动刷新失败，表现为"保存即掉线"；
 *   4. 每个 Label 都有对应控件 id（键盘/读屏可达）；
 *   5. 页面不重复声明 ssr:false —— /account/** 的 SPA 反选由 routeRules 单源负责；
 *   6. 四语 account.* 文案齐备。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const pagePath = resolve(ROOT, 'pages/account/settings.vue')
const page = readFileSync(pagePath, 'utf-8')
const listPage = readFileSync(resolve(ROOT, 'pages/account/index.vue'), 'utf-8')

const NEW_KEYS = [
  'settingsTitle', 'settingsDesc', 'backToAccount',
  'sectionProfile', 'sectionProfileHint',
  'sectionPrivacy', 'sectionPrivacyHint',
  'sectionPassword', 'sectionPasswordHint',
  'fieldNickname', 'fieldBio', 'fieldWebsite', 'fieldGithub', 'fieldQq',
  'fieldAvatarSource', 'fieldAvatarSourceHint',
  'avatarSourceAuto', 'avatarSourceCustom', 'avatarSourceGithub', 'avatarSourceQq', 'avatarSourceGravatar',
  'saveProfile', 'profileSaved', 'tooLong',
  'prefPublicProfile', 'prefPublicProfileHint',
  'prefShowEmail', 'prefShowEmailHint',
  'prefShowPosts', 'prefShowPostsHint',
  'prefShowComments', 'prefShowCommentsHint',
  'prefShowStats', 'prefShowStatsHint',
  'savePreferences', 'preferencesSaved',
  'fieldOldPassword', 'fieldNewPassword', 'fieldConfirmPassword',
  'savePassword', 'passwordChanged', 'passwordMismatch'
]

/** 抽出 `const preferences = reactive<UserPreferences>({ ... })` 里的键名 */
function preferenceKeys(source: string): string[] {
  const start = source.indexOf('const preferences = reactive<UserPreferences>(')
  expect(start, 'preferences 响应式对象不存在').toBeGreaterThan(-1)
  const end = source.indexOf('})', start)
  const body = source.slice(start, end)
  return [...body.matchAll(/^\s{2}(\w+):/gm)].map(m => m[1] as string)
}

describe('账户设置 /account/settings', () => {
  it('三个写端点都有真实调用，且都走 apiFetch', () => {
    for (const [path, method] of [
      ['/users/me', 'PUT'],
      ['/users/me/preferences', 'PUT'],
      ['/users/me/password', 'POST']
    ]) {
      const re = new RegExp(`\\(\\s*'?${path}'?\\s*,\\s*\\{[^}]*method: '${method}'`, 's')
      expect(page, `缺少 apiFetch ${method} ${path}`).toMatch(re)
    }
    expect(page).toMatch(/useAPI<[\s\S]{0,160}'\/users\/me\/preferences'/)
    // 不裸用 $fetch：会绕过统一信封与 401 刷新链
    expect(page).not.toContain('$fetch(')
  })

  it('资料保存后回读 store，顶栏与作者卡片才不会停在旧值', () => {
    expect(page).toContain('await authStore.fetchUser()')
  })

  it('隐私开关精确等于后端有强制点的 5 个字段，不含死字段 theme', () => {
    expect(preferenceKeys(page)).toEqual([
      'public_profile', 'show_email', 'show_posts', 'show_comments', 'show_stats'
    ])
  })

  it('改密成功即清登录态并跳登录页', () => {
    const at = page.search(/'\/users\/me\/password'/)
    const tail = page.slice(at, at + 600)
    expect(tail).toContain('authStore.clearTokens()')
    expect(tail).toMatch(/navigateTo\('\/login'\)/)
  })

  it('每个 Label 都有对应控件 id', () => {
    const labelFor = [...page.matchAll(/<Label[^>]*\bfor="([^"]+)"/g)].map(m => m[1] as string)
    expect(labelFor.length).toBeGreaterThanOrEqual(9)
    for (const id of labelFor) {
      expect(page, `控件 id=${id} 缺失`).toContain(`id="${id}"`)
    }
  })

  it('SPA 口径单源：页面不再写第二份 ssr:false，列表页给出入口', () => {
    expect(page).not.toContain('ssr: false')
    expect(page).toMatch(/middleware: 'auth-required'/)
    expect(listPage).toMatch(/navigateTo\('\/account\/settings'\)/)
  })

  it.each(['zh', 'en', 'ja', 'zh_Hant'] as const)('%s 具备账户设置文案键', (locale) => {
    const messages = JSON.parse(
      readFileSync(resolve(ROOT, `i18n/locales/${locale}.json`), 'utf-8')
    ) as Record<string, Record<string, string>>
    for (const key of NEW_KEYS) {
      expect(messages.account?.[key], `${locale} 缺 account.${key}`).toBeTruthy()
    }
  })
})
