/**
 * 友链公开申请（批次 #113）四段接线契约：开关 → 写口 → pending 队列 → 前台表单。
 *
 * 这一族的半成品形态都很安静，而且都"看起来在做"：
 * - 后端加了 `features.enable_friend_apply` 但没人读 → 后台那个开关是假的；
 * - 接口写好了但 /friends 页没有表单 → 功能等于不存在（批次 #112 退役的那个友链申请
 *   扁平文案键就是这种：存得进、没人读）；
 * - 表单出现但没接验证码组件 → 后台开着 `enable_captcha` 时访客只看到一句 400；
 * - 文案只加中文 → 日语页面显示裸 key `friends.applyTitle`。
 * 所以按"集合相等"与"真实消费点"两头钉。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(process.cwd())
const BACKEND_ROOT = resolve(ROOT, '..')
const read = (...parts: string[]) => readFileSync(resolve(...parts), 'utf-8')
const readFrontend = (...parts: string[]) => read(ROOT, ...parts)
const readBackend = (...parts: string[]) => read(BACKEND_ROOT, ...parts)

const coreApi = readBackend('backend', 'api', 'core.py')
const schemas = readBackend('backend', 'schemas', '__init__.py')
const settingsGroups = readBackend('backend', 'api', 'settings_groups.py')
const friendsPage = readFrontend('pages', 'friends.vue')
const useSite = readFrontend('composables', 'useSite.ts')
const settingsPage = readFrontend('pages', 'admin', 'system', 'settings.vue')

const LOCALES = ['zh', 'en', 'ja', 'zh_Hant']

/** 从 `marker` 之后起截到下一个匹配 `nextRe` 的位置（找不到就截到文件尾）。 */
function sliceFrom(src: string, marker: string, nextRe: RegExp, label: string): string {
  const start = src.indexOf(marker)
  if (start < 0) throw new Error(`找不到 ${label}——源码形态变了，要同步改本测试`)
  const rest = src.slice(start + marker.length)
  const end = rest.search(nextRe)
  return end < 0 ? rest : rest.slice(0, end)
}

const applyModelBody = () =>
  sliceFrom(schemas, 'class FriendLinkApply(BaseModel):', /^class /m, 'FriendLinkApply 请求模型')

const applyHandlerBody = () =>
  sliceFrom(coreApi, 'async def apply_friend_link', /^@router/m, 'apply_friend_link 处理函数')

function friendsKeys(locale: string): string[] {
  const dict = JSON.parse(readFrontend('i18n', 'locales', `${locale}.json`)) as {
    friends: Record<string, unknown>
  }
  return Object.keys(dict.friends).sort()
}

describe('友链申请写入口', () => {
  it('匿名写口存在，且带限流、开关与验证码三道闸门', () => {
    expect(coreApi).toContain('"/friend-links/apply"')
    expect(coreApi).toContain('async def apply_friend_link')
    expect(coreApi).toContain('rate_limit_sensitive("friend_link_apply")')
    expect(coreApi).toContain('bool_of(feats, "enable_friend_apply"')
    expect(coreApi).toContain('FRIEND_APPLY_DISABLED')
    expect(coreApi).toContain('ensure_captcha_for_guest')
  })

  it('一律以 pending 落库，且不清缓存（pending 不在公示谓词里）', () => {
    const body = applyHandlerBody()
    expect(body).toContain('status=FriendLink.STATUS_PENDING')
    expect(body).toContain('is_active=False')
    expect(body, '申请表单没有排序权重与开新窗的裁决权，写死默认值').toContain('order=0')
    expect(body, 'pending 行对外不可见，清缓存等于白清（还多打一次 Nitro）')
      .not.toMatch(/invalidate_cache\(\s*['"]friend_links['"]\s*\)/)
  })

  it('提交者写不出档位：extra=forbid 且四个裁决字段不在请求模型里', () => {
    const body = applyModelBody()
    expect(body).toMatch(/model_config = \{\s*["']extra["']: ["']forbid["']\s*\}/)
    for (const field of ['status', 'is_active', 'order', 'target_blank']) {
      expect(body, `FriendLinkApply 里出现了 ${field}——等于让提交者自己批准自己`)
        .not.toMatch(new RegExp(`^\\s{4}${field}:`, 'm'))
    }
    // 会渲染到访客页面上的短字段必须拒标记字符（AGENTS §12.8）
    expect(body).toContain('pattern=_NO_MARKUP_PATTERN')
    expect(body).toContain('_require_absolute_url')
  })
})

describe('features.enable_friend_apply 开关必须有执行者与消费方', () => {
  it('后端分组默认值里有这一项（否则设置页提交即被静默丢弃）', () => {
    const block = settingsGroups.split('def _default_features')[1] ?? ''
    expect(block).toMatch(/"enable_friend_apply": False,/)
  })

  it('useSite 的 features 投影暴露它，默认 false', () => {
    expect(useSite).toMatch(/enable_friend_apply: flag\('enable_friend_apply', false\)/)
  })

  it('后台设置页有中文名、默认值表和帮助文案三处登记', () => {
    expect(settingsPage).toMatch(/enable_friend_apply: '[^']*'/)
    expect(settingsPage).toMatch(/enable_friend_apply: false[ },]/)
    expect(settingsPage, '开关的副作用（表单出现在 /friends、提交一律进待审核队列）必须写在帮助里')
      .toMatch(/enable_friend_apply: '[^']*待审核[^']*'/)
  })

  it('前台表单以这一项为渲染条件（关掉不留点了就 403 的按钮）', () => {
    expect(friendsPage).toContain('site.features.value.enable_friend_apply')
    expect(friendsPage).toMatch(/const applyEnabled = computed\(\(\) => site\.features\.value\.enable_friend_apply\)/)
    expect(friendsPage).toMatch(/<Card\s+v-if="applyEnabled"/)
  })
})

describe('/friends 页的申请表单接线', () => {
  it('打到 POST /friend-links/apply，带 name/url 与可选字段', () => {
    expect(friendsPage).toContain('apiFetch<FriendLinkApplyReceipt>(\'/friend-links/apply\'')
    expect(friendsPage).toContain('method: \'POST\'')
    expect(friendsPage).toMatch(/const payload: Record<string, string> = \{ name, url, \.\.\.\(captchaRef\.value\?\.payload\(\) \?\? \{\}\)/)
    expect(friendsPage).toContain('payload.description =')
    expect(friendsPage).toContain('payload.logo =')
  })

  it('验证码闸门同评论/留言同轨：只在未登录 + 后台开验证码时出现，失败后换一张', () => {
    expect(friendsPage).toMatch(/const needCaptcha = computed\(\(\) => !authStore\.isAuthenticated && site\.features\.value\.enable_captcha\)/)
    expect(friendsPage).toContain('<CaptchaField')
    expect(friendsPage).toMatch(/v-if="needCaptcha"/)
    expect(friendsPage).toMatch(/if \(needCaptcha\.value\) captchaRef\.value\?\.refresh\(\)/)
    expect(friendsPage).toContain('captchaRef.value?.valid()')
  })

  it('校验与失败都走行内提示（apiFetch 已全局 toast，不得双报）', () => {
    expect(friendsPage).toMatch(/const submitError = ref<string \| null>\(null\)/)
    expect(friendsPage).toContain('v-if="submitError"')
    expect(friendsPage).toContain('extractApiErrorMessage(e.data, String(t(\'friends.applyFailed\')))')
    expect(friendsPage, '绝对地址在前端先判一次，后端 422 是兜底不是首道门')
      .toContain('URL_SCHEME_RE = /^https?:\\/\\//i')
    expect(friendsPage).toContain('URL_SCHEME_RE.test(url)')
  })

  it('提交成功不刷新公示列表：pending 行对外不可见，刷新只会拿到同一份数据', () => {
    expect(friendsPage).not.toMatch(/await refresh/)
  })
})

describe('申请文案四语一致', () => {
  it('四个 locale 的 friends 键集合完全相等（漏一语即页面显示裸 key）', () => {
    const expected = friendsKeys('zh')
    for (const locale of LOCALES) {
      expect(friendsKeys(locale), `${locale}.friends 与 zh 键集不等`).toEqual(expected)
    }
  })

  it('页面用到的 friends.* 与 captcha.required 在四语里都有值', () => {
    const used = [...friendsPage.matchAll(/t\('(friends\.[A-Za-z0-9]+)'\)/g)]
      .map(m => m[1] as string)
      .map(k => k.split('.')[1] as string)
    expect(used.length).toBeGreaterThan(8)
    for (const locale of LOCALES) {
      const dict = JSON.parse(readFrontend('i18n', 'locales', `${locale}.json`)) as {
        friends: Record<string, string>
        captcha: Record<string, string>
      }
      for (const key of new Set(used)) {
        expect(dict.friends[key], `${locale}.friends.${key}`).toBeTruthy()
      }
      expect(dict.captcha.required, `${locale}.captcha.required`).toBeTruthy()
    }
  })
})
