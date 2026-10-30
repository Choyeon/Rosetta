/**
 * 账户设置 /account/settings 契约（静态源码断言）。
 *
 * 这一页把 users 模块里"后端就绪、前端零消费"的自服务写端点接上：
 * PUT /users/me、PUT /users/me/preferences、POST /users/me/password、DELETE /users/me
 * （GET /users/me/preferences 由 useAPI 消费）。钉住的口径：
 *   1. 写请求全部走 apiFetch（统一失败信封 + toast），取数据走 useAPI；
 *   2. 隐私开关只暴露**后端真有强制点**的 7 个字段。UserPreference.theme 是死字段
 *      （models/user.py 里唯一引用是 __repr__），放开关等于给用户一个不生效的设置；
 *   3. 改密成功必须 clearTokens + 跳 /login：后端 bump token_version 让全部会话失效，
 *      留在原页只会让下一个请求撞 401 自动刷新失败，表现为"保存即掉线"；
 *   4. 每个 Label 都有对应控件 id（键盘/读屏可达）；
 *   5. 页面不重复声明 ssr:false —— /account/** 的 SPA 反选由 routeRules 单源负责；
 *   6. 四语 account.* 文案齐备；
 *   7. 注销（DELETE /users/me）：密码走请求体，成功必须 clearTokens 并离页，
 *      超管档不给表单（后端对 is_superuser 直接 403，让人填完密码才吃错不算守）。
 *   8. 自定义头像：上传（POST /media/avatar）→ avatar 字段 → 来源切 custom → 同一写口保存。
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
  'fieldAvatar', 'fieldAvatarHint', 'avatarUpload', 'avatarReplace', 'avatarRemove', 'avatarNone',
  'fieldAvatarSource', 'fieldAvatarSourceHint',
  'avatarSourceAuto', 'avatarSourceCustom', 'avatarSourceGithub', 'avatarSourceQq', 'avatarSourceGravatar',
  'saveProfile', 'profileSaved', 'tooLong',
  'prefPublicProfile', 'prefPublicProfileHint',
  'prefShowEmail', 'prefShowEmailHint',
  'prefShowPosts', 'prefShowPostsHint',
  'prefShowComments', 'prefShowCommentsHint',
  'prefShowStats', 'prefShowStatsHint',
  'prefShowSocialLinks', 'prefShowSocialLinksHint',
  'savePreferences', 'preferencesSaved',
  'fieldOldPassword', 'fieldNewPassword', 'fieldConfirmPassword',
  'savePassword', 'passwordChanged', 'passwordMismatch',
  'sectionDeleteAccount', 'sectionDeleteAccountHint', 'deleteAccountSuperAdmin',
  'deleteAccountNoticeUnavailable', 'deleteAccountNoticeContent', 'deleteAccountNoticeSessions',
  'deleteAccountPasswordField', 'deleteAccountConfirmCheckbox', 'deleteAccountButton',
  'deleteAccountNeedFields', 'deleteAccountDone'
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
  it('四个写端点都有真实调用，且都走 apiFetch', () => {
    for (const [path, method] of [
      ['/users/me', 'PUT'],
      ['/users/me/preferences', 'PUT'],
      ['/users/me/password', 'POST'],
      ['/users/me', 'DELETE']
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

  it('偏好开关精确等于后端有强制点的 7 个字段，不含死字段 theme', () => {
    // 前六条存 user_preferences，notify_by_email 存 User 行（评论通知邮件按它筛收件人）；
    // 判定口径不变：后端没有真实强制点的键不得进这张清单（theme 就是那条死字段）。
    expect(preferenceKeys(page)).toEqual([
      'public_profile', 'show_email', 'show_posts', 'show_comments', 'show_stats',
      'show_social_links', 'notify_by_email'
    ])
  })

  it('改密成功即清登录态并跳登录页', () => {
    const at = page.search(/'\/users\/me\/password'/)
    const tail = page.slice(at, at + 600)
    expect(tail).toContain('authStore.clearTokens()')
    expect(tail).toMatch(/navigateTo\('\/login'\)/)
  })

  it('注销成功即清登录态并离开本页，提示走本地文案', () => {
    const at = page.search(/method: 'DELETE'/)
    expect(at, '注销请求没发出去').toBeGreaterThan(-1)
    const tail = page.slice(at, at + 900)
    expect(tail).toContain('authStore.clearTokens()')
    expect(tail).toMatch(/navigateTo\('\/'\)/)
    // 后端那条 message 是写死的中文，四语站点不能直接抬上来
    expect(tail).toMatch(/toast\.success\(t\('account\.deleteAccountDone'\)\)/)
    expect(tail).not.toMatch(/res\?\.message/)
  })

  it('注销密码走请求体、不走查询串', () => {
    const at = page.search(/method: 'DELETE'/)
    const tail = page.slice(at, at + 400)
    expect(tail).toMatch(/body: \{ password: deleteForm\.password \}/)
    expect(tail).not.toMatch(/password=.*\$fetch|\?password/)
  })

  it('没勾确认或空密码不发请求，超管档不给表单（后端对 is_superuser 直接 403）', () => {
    const at = page.search(/async function deleteAccount/)
    expect(at, 'deleteAccount 处理函数不存在').toBeGreaterThan(-1)
    const head = page.slice(at, at + 400)
    expect(head).toMatch(/if \(!deleteForm\.password \|\| !deleteForm\.confirmed\)/)
    expect(head).toMatch(/return/)
    expect(page).toMatch(/v-if="isSuperAdmin"/)
    expect(page).toMatch(/v-else\s+class="mt-6 flex flex-col gap-4"/)
    expect(page).toMatch(/authUser\.value\?\.is_superuser === true/)
  })

  it('每个 Label 都有对应控件 id', () => {
    const labelFor = [...page.matchAll(/<Label[^>]*\bfor="([^"]+)"/g)].map(m => m[1] as string)
    expect(labelFor.length).toBeGreaterThanOrEqual(9)
    for (const id of labelFor) {
      expect(page, `控件 id=${id} 缺失`).toContain(`id="${id}"`)
    }
  })

  it('自定义头像四段齐全：上传口 → avatar 字段 → 来源切 custom → raw 列回填', () => {
    // 「头像来源」里本来就有 custom 一档，缺了这四段时它只是一块首字母色块
    expect(page).toContain('useMediaUploadAvatar')
    expect(page).toMatch(/const res = await useMediaUploadAvatar\(file\)/)
    // 上传即代表想用这张图：不把来源切到 custom，选着 QQ 来源的用户会以为上传失败
    expect(page).toMatch(/profile\.avatar = res\.url[\s\S]{0,120}profile\.avatar_source = 'custom'/)
    // 移除后来源停在 custom 等于给用户一块空色块，回到 auto 才能继续按 QQ/GitHub 解析
    expect(page).toMatch(/profile\.avatar = ''[\s\S]{0,160}profile\.avatar_source = 'auto'/)
    // 写入走同一个资料写口（PUT /users/me），清空写 null
    expect(page).toMatch(/avatar: profile\.avatar \|\| null/)
    // 回填必须是 raw 列：拿 resolved_avatar_url 回填会把派生直链固化进自定义头像列
    expect(page).toMatch(/profile\.avatar = String\(u\.avatar \?\? ''\)/)
    expect(page).not.toMatch(/profile\.avatar = String\(u\.resolved_avatar_url/)
  })

  it('SPA 口径单源：页面不再写第二份 ssr:false，列表页给出入口', () => {
    expect(page).not.toContain('ssr: false')
    expect(page).toMatch(/middleware: 'auth-required'/)
    // 入口跳转必须过 localeHref：写死裸路径会让 /en /ja /zh_Hant 下的「账户设置」掉回中文地址。
    expect(listPage).toMatch(/navigateTo\(localeHref\('\/account\/settings'\)\)/)
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
