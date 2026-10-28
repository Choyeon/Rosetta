/**
 * 「评论通知邮件」偏好（`notify_by_email`）读写两端接线的守卫。
 *
 * 这一族此前的形状是**半接通**：`User.notify_by_email` 列存在、
 * 评论扇出真的按它筛选收件人，但偏好接口的请求/响应模型都不带这个键，
 * 账号设置页也没有开关 —— 站点配好 SMTP 后每个人都会被邮件联系，且无处关闭。
 *
 * 五条口径必须钉住：
 * * 后端两个模型（写口 UserPreferenceUpdate / 读口 UserPreferenceResponse）都声明这一项。
 * * 服务层把它**分流到 User 行**：那份从 UserPreference 模型派生的白名单永远筛不出它，
 *   漏一处就是"接口 200、前端提示已保存、库里一个字节没改"。
 * * 端点响应从 User 行补值（两条口共用同一个拼装 helper），
 *   不补的表现是"已关闭的用户刷新后开关又亮着"。
 * * 匿名公开口（UserPreferencesPublicDoc）不得出现这一项。
 * * 前端默认值 true 与列的 server_default 同数，且真的进了表单项。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')

// 仓库混用 CRLF 与 LF：多行标记必须先归一，否则 indexOf 永远找不到
function readSource(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')
}

const schemas = readSource('../backend/schemas/__init__.py')
const endpoints = readSource('../backend/api/users.py')
const service = readSource('../backend/services/user_service.py')
const page = readSource('pages/account/settings.vue')

function count(source: string, needle: string): number {
  return source.split(needle).length - 1
}

describe('评论通知邮件偏好接线', () => {
  it('后端两个偏好模型都声明这一项（写口 + 本人读口）', () => {
    const update = schemas.slice(
      schemas.indexOf('class UserPreferenceUpdate('),
      schemas.indexOf('class PasswordChange(')
    )
    const response = schemas.slice(
      schemas.indexOf('class UserPreferenceResponse('),
      schemas.indexOf('class UserPreferenceUpdate(')
    )
    expect(update).toContain('notify_by_email: bool | None = None')
    expect(response).toContain('notify_by_email: bool = Field(')
    // 默认值必须与 User.notify_by_email 的 server_default 同数：
    // 忘记补值时它替真值说话，报的就是"已开启"
    expect(response).toMatch(/notify_by_email: bool = Field\(\s*True,/)
  })

  it('服务层把这一项分流到 User 行，而不是让派生白名单静默丢弃', () => {
    expect(service).toContain('_USER_SIDE_PREFERENCE_FIELDS: frozenset[str] = frozenset({"notify_by_email"})')
    const fn = service.slice(
      service.indexOf('async def update_preferences('),
      service.indexOf('async def change_password(')
    )
    expect(fn).toContain('data.get("notify_by_email")')
    expect(fn).toContain('k not in _USER_SIDE_PREFERENCE_FIELDS')
    expect(fn).toContain('user_row.notify_by_email = bool(notify_by_email)')
    // 白名单过滤必须走分流后的 pref_source，否则日志会把这个键报成"未知字段"
    expect(fn).toContain('{k: v for k, v in pref_source.items() if k in allowed_fields}')
  })

  it('两条本人口都从 User 行补值并经同一拼装 helper（少一处即"刷新后开关亮回去"）', () => {
    expect(endpoints).toContain('async def _notify_by_email_flag(')
    expect(endpoints).toContain('select(User.notify_by_email).where(User.id == user_id)')
    expect(endpoints).toContain('def _preferences_response(')
    expect(count(endpoints, '_preferences_response(')).toBeGreaterThanOrEqual(3)
    expect(count(endpoints, '_notify_by_email_flag(db, current_user.id)')).toBeGreaterThanOrEqual(2)
    // 端点不得再直接 model_validate 偏好对象：那样这一项永远是模型默认值
    const getMe = endpoints.slice(
      endpoints.indexOf('async def get_my_preferences('),
      endpoints.indexOf('def _profile_is_hidden(')
    )
    expect(getMe).not.toContain('return UserPreferenceResponse.model_validate')
  })

  it('匿名公开隐私口不摊这一项（只有本人接口可读）', () => {
    const doc = endpoints.slice(
      endpoints.indexOf('class UserPreferencesPublicDoc('),
      endpoints.indexOf('class UserStatsDoc(')
    )
    expect(doc).not.toBe('')
    expect(doc).not.toContain('notify_by_email')
    expect(doc).toContain('show_stats: bool')
    // 公开口的响应体是端点里手写的裸 dict，字段清单必须仍是那 5 个隐私开关
    const publicEndpoint = endpoints.slice(
      endpoints.indexOf('async def get_user_preferences_by_username('),
      endpoints.indexOf('@router.get(\n    "/",')
    )
    expect(publicEndpoint).not.toContain('notify_by_email')
    expect(count(publicEndpoint, '"show_stats":')).toBe(2)
  })

  it('账号设置页把这一项当开关渲染，默认值与后端同数', () => {
    expect(page).toContain('notify_by_email: boolean')
    expect(page).toContain('notify_by_email: true')
    expect(page).toContain('preferences.notify_by_email = data.notify_by_email ?? true')
    expect(page).toMatch(/key: 'notify_by_email' as const/)
    expect(page).toMatch(/label: t\('account\.prefNotifyEmail'\)/)
    // 保存走整份 preferences 展开：单独列字段等于再加一处会漏的白名单
    const save = page.slice(page.indexOf('async function savePreferences('))
    expect(save).toContain('body: { ...preferences }')
  })

  it('四语 locale 都登记了标签与提示', () => {
    for (const code of ['zh', 'en', 'ja', 'zh_Hant']) {
      const dict = JSON.parse(
        readFileSync(resolve(ROOT, 'i18n/locales', `${code}.json`), 'utf8')
      ) as { account?: { prefNotifyEmail?: string, prefNotifyEmailHint?: string } }
      const label = dict.account?.prefNotifyEmail ?? ''
      const hint = dict.account?.prefNotifyEmailHint ?? ''
      expect(label, `${code} 缺 account.prefNotifyEmail`).not.toBe('')
      expect(hint, `${code} 缺 account.prefNotifyEmailHint`).not.toBe('')
      expect(hint).not.toContain('{')
    }
  })
})
