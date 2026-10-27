/**
 * 文章「密码提示」（`encryption_hint`）读写两端接线的守卫。
 *
 * 这一族此前的形状是**半接通**：`Post.encryption_hint` 列存在、`PostCreate`/`PostUpdate`
 * 收这个键、闸门页 `pages/posts/[slug].vue` 也在读 `detail.encryption_hint`，
 * 但详情响应模型不带这个键、编辑器表单从不发送 —— 于是锁屏上的提示永远不出现，
 * 后台多一个"填了没反应"的字段（与已退役的调色板一族同一种缺陷形状）。
 *
 * 四条口径必须钉住，任何一条改坏都是静默失效：
 * * 写口始终发送 `encryption_hint`（空串是合法值 = "作者不要提示了"），
 *   且**绝不能用 `form.password` 那种"空则不发"的规则**——那会让提示永远删不掉。
 * * 编辑口回填：不回填等于每次 PUT 把提示提交成空串，改一次标题就清掉它。
 * * 读口字段名与后端响应模型逐字一致（前端读 `encryption_hint`，不是 `hint`）。
 * * 提示只在"真有密码哈希"时出现，所以表单里的输入框必须锁在 `visibility === 'password'`。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const form = readFileSync(resolve(ROOT, 'components/admin/PostForm.vue'), 'utf8')
const reader = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf8')
const schemas = readFileSync(resolve(ROOT, '../backend/schemas/__init__.py'), 'utf8')

function section(source: string, startMarker: string, endMarker: string): string {
  const start = source.indexOf(startMarker)
  expect(start, `源码里找不到起点：${startMarker}`).toBeGreaterThanOrEqual(0)
  const rest = source.slice(start)
  const end = rest.indexOf(endMarker)
  expect(end, `源码里找不到终点：${endMarker}（起点 ${startMarker}）`).toBeGreaterThan(-1)
  return rest.slice(0, end)
}

describe('文章密码提示接线', () => {
  it('编辑器表单声明该字段并绑定两个输入框（密码 + 提示）', () => {
    expect(form).toContain('encryption_hint: \'\',')
    expect(form).toContain('v-model="form.encryption_hint"')
    // 输入框必须锁在密码态：公开/私密文章不该出现"提示"控件
    const hintInput = section(form, 'v-model="form.encryption_hint"', '/>')
    expect(hintInput).not.toContain('type="password"')
    const passwordAt = form.indexOf('v-model="form.password"')
    const hintAt = form.indexOf('v-model="form.encryption_hint"')
    const block = form.slice(passwordAt, hintAt)
    expect(passwordAt).toBeGreaterThanOrEqual(0)
    expect(hintAt).toBeGreaterThan(passwordAt)
    expect(block).toContain('v-if="form.visibility === \'password\'"')
  })

  it('写口始终发送提示，与 password 的"空则不发"规则明确分开', () => {
    const payload = section(form, 'const buildPayload', 'const validateBase')
    expect(payload).toContain('payload.encryption_hint =')
    expect(payload).toMatch(/payload\.password = form\.password/)
    // 提示不区分"是否输入过密码"：离开密码态也要把旧值清掉
    expect(payload).toContain('form.visibility === \'password\' ? form.encryption_hint.trim() : \'\'')
  })

  it('编辑口回填提示（否则一次普通保存就清空它）', () => {
    const hydrate = section(form, 'const applyInitialData', 'const saveDraftToLocalStorage')
    expect(hydrate).toContain('form.encryption_hint = data.encryption_hint')
  })

  it('提示不得写成密码本身（锁屏明文 = 公开口令）', () => {
    const validate = section(form, 'const validateBase', 'const markSubmitted')
    expect(validate).toContain('form.encryption_hint.trim() === form.password.trim()')
  })

  it('闸门页读 encryption_hint，且后端响应模型声明同名可空字段', () => {
    expect(reader).toMatch(/const rawHint = detail\.encryption_hint\s*\n/)
    // 上面这条要求"行尾就是它"：`?? detail.hint` 这个别名曾挂在读侧，而 `hint`
    // 没有任何文章端点产出过（OOBE 的 hint 是另一族诊断字段）。
    expect(reader).toContain('postEncryptionHint')
    // 公开读口（PostLocalizedResponse）与后台编辑口（PostEditResponse）都要带这个键，
    // 少一条的表现：前台永远读不到提示，或编辑器每次 PUT 都把它写成空
    const declared = schemas.match(/encryption_hint: str \| None = None/g) ?? []
    expect(declared.length).toBeGreaterThanOrEqual(2)
  })

  it('四语 locale 都登记了提示字段的 aria-label 键', () => {
    for (const code of ['zh', 'en', 'ja', 'zh_Hant']) {
      const dict = JSON.parse(
        readFileSync(resolve(ROOT, 'i18n/locales', `${code}.json`), 'utf8')
      ) as { admin?: { editor?: { postPasswordHint?: string } } }
      const hint = dict.admin?.editor?.postPasswordHint ?? ''
      expect(hint, `${code} 缺 admin.editor.postPasswordHint`).not.toBe('')
      expect(hint).not.toContain('{')
    }
  })
})
