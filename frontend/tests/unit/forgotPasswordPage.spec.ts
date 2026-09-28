/**
 * 找回密码页契约（静态扫描，不开浏览器）：钉住三件容易在重构中静默失效的事——
 * 1. 两个端点必须真的被调用，且 body 字段名与后端 _PasswordResetRequest / _PasswordResetBody 一致
 *    （字段名改了不会报错，只会 422，而后端对"账号不存在"也回 200，前端极易误判成成功）；
 * 2. 发码后的提示文案必须取后端返回值，不得由前端自造"账号存在"判断（防枚举口径）；
 * 3. /login 的「忘记密码」入口必须是真链接，且历史遗留的"暂未开放"禁用态与死键彻底清除。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const page = readFileSync(resolve(process.cwd(), 'pages/forgot-password.vue'), 'utf8')
const login = readFileSync(resolve(process.cwd(), 'pages/login.vue'), 'utf8')
const locales = ['zh', 'en', 'ja', 'zh_Hant'].map(loc => ({
  loc,
  data: JSON.parse(
    readFileSync(resolve(process.cwd(), `i18n/locales/${loc}.json`), 'utf8')
  ) as Record<string, Record<string, string>>
}))

function postsTo(path: string): boolean {
  return new RegExp(`\\(\\s*'?${path}'?\\s*,\\s*\\{[^}]*method: 'POST'`, 's').test(page)
}

/** 取顶层文案段：noUncheckedIndexedAccess 下索引结果可能 undefined，统一收口一次。 */
function section(data: Record<string, Record<string, string>>, name: string): Record<string, string> {
  return data[name] ?? {}
}

describe('pages/forgot-password.vue', () => {
  it('两个重置端点都以 POST 真实调用，且经由 apiFetch（不裸用 $fetch）', () => {
    // 前缀必须是 /users：这两条挂在 users.router（/api/users）下，不是 blog 的 /users/me/*。
    // 写错前缀页面只会静默 404，由 tests/test_frontend_api_path_parity.py 对照 OpenAPI 抓住。
    expect(postsTo('/users/password-reset-request')).toBe(true)
    expect(postsTo('/users/password-reset')).toBe(true)
    expect(page).toContain('apiFetch')
    expect(page).not.toContain('$fetch(')
  })

  it('请求体字段名与后端 schema 逐字一致', () => {
    expect(page).toContain('email_or_username:')
    expect(page).toContain('token_or_email:')
    expect(page).toContain('code:')
    expect(page).toContain('new_password:')
  })

  it('发码提示取后端 message，前端不自造"账号是否存在"的判断', () => {
    expect(page).toMatch(/res\?\.message\s*\|\|/)
    expect(page).not.toContain('账号不存在')
  })

  it('验证码形态按后端约束（6 位数字）预校验，密码强度交给后端单通道', () => {
    expect(page).toMatch(/\\d\{6\}/)
    expect(page).not.toMatch(/password.*length\s*>=\s*8/s)
  })

  it('每个 Label 的 for 都有同 id 的控件', () => {
    const fors = [...page.matchAll(/<Label[^>]*for="([^"]+)"/g)].map(m => m[1]!)
    expect(fors.length).toBeGreaterThan(0)
    for (const id of fors) {
      expect(page, `缺少 id="${id}" 的表单控件`).toContain(`id="${id}"`)
    }
  })

  it('渲染开关不写在页面里（routeRules 是单源）', () => {
    expect(page).not.toContain('ssr: false')
  })
})

describe('/login 找回密码入口', () => {
  it('两套登录骨架都指向 /forgot-password，历史"暂未开放"禁用态已清除', () => {
    const links = [...login.matchAll(/to="\/forgot-password"/g)]
    expect(links.length).toBe(2)
    // 精确到"禁用 span 包住 forgotPassword 文案"这一形状：按钮上的 disabled:cursor-not-allowed
    // 是合法样式，宽口径断言会把它们一起算成失败。
    expect(login).not.toMatch(/aria-disabled="true"[^>]*>\s*\{\{\s*t\('auth\.forgotPassword'\)\s*\}\}/)
    expect(login).not.toContain('forgotPasswordDisabled')
  })
})

describe('i18n · forgotPassword 四语齐备', () => {
  const KEYS = [
    'title', 'desc', 'step1Title', 'step2Title', 'fieldAccount', 'fieldCode',
    'fieldNewPassword', 'fieldConfirmPassword', 'sendCode', 'codeSent',
    'resetPassword', 'passwordReset', 'passwordMismatch', 'backToLogin', 'devCodeHint'
  ]

  it.each(KEYS)('每个语言都有 forgotPassword.%s 且非空', (key) => {
    for (const { loc, data } of locales) {
      const block = section(data, 'forgotPassword')
      expect(Object.keys(block).length, `${loc}.json 缺 forgotPassword 段`).toBeGreaterThan(0)
      expect(block[key], `${loc}.json 缺 forgotPassword.${key}`).toBeTruthy()
    }
  })

  it('页面用到的键在四语里都存在（防 t() 回落成裸键名）', () => {
    const used = [...page.matchAll(/t\('forgotPassword\.([A-Za-z0-9_]+)'/g)].map(m => m[1]!)
    expect(used.length).toBeGreaterThan(8)
    for (const key of new Set(used)) {
      expect(KEYS, `页面用了未登记键 forgotPassword.${key}`).toContain(key)
    }
  })

  it('「暂未开放」死键已从四语删除（入口已接通，留着就是与代码矛盾的文案库存）', () => {
    for (const { loc, data } of locales) {
      expect(section(data, 'auth').forgotPasswordDisabled, `${loc}.json 仍有死键`).toBeUndefined()
    }
  })
})
