/**
 * 站点设置：多语言 dict 字段必须用四语 Tab 编辑器，不能落进「JSON 数组」裸文本域。
 *
 * 真实缺陷：inferSchema 对 `typeof value === 'object'` 一律当通用 JSON 渲染，
 * 于是 hero.cta_text / donate.title / donate.description 这三个 i18n dict：
 *   ① 提示写成「数组每项应为对象」（它们是对象不是数组，提示与实际形状矛盾）；
 *   ② 编辑器只能改库里已经存在的语言键——种子数据只有 {zh, en}，
 *      ja / zh_Hant 从此再也补不进去，四语站点永远缺两种语言。
 * 现在判定收敛到 `isI18nDict`（composables/useAdminI18n.ts），命中即走 I18nTabsEditor
 * （固定四语 Tab，首次编辑就把值升级成完整四键 dict）。
 *
 * 本用例两头都钉：纯函数判定（含反例）+ 页面接线（判定必须早于通用 object 分支），
 * 并回读后端 `_default_hero/_default_donate` 确认这几条键在真实 API 回包里确实是 locale dict。
 */
import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import process from 'node:process'
import { isI18nDict } from '../../composables/useAdminI18n'

const FE_ROOT = process.cwd().replace(/[\\/]$/, '')
const SETTINGS_VUE = `${FE_ROOT}/pages/admin/system/settings.vue`
const GROUPS_PY = `${FE_ROOT}/../backend/api/settings_groups.py`

describe('isI18nDict：判定口径', () => {
  it('四语 dict 与只写了两语的存量值都算多语言字段', () => {
    expect(isI18nDict({ zh: '开始阅读', en: 'Start Reading', ja: '', zh_Hant: '' })).toBe(true)
    expect(isI18nDict({ zh: '开始阅读', en: 'Start Reading' })).toBe(true)
    expect(isI18nDict({ ja: 'ようこそ' })).toBe(true)
    expect(isI18nDict({ zh: null, en: 'x' })).toBe(true)
  })

  it('标量 / 空对象 / 数组都不算', () => {
    for (const v of [null, undefined, '', '开始阅读', 0, false, [], {}]) {
      expect(isI18nDict(v), `${JSON.stringify(v)} 被误判成 i18n dict`).toBe(false)
    }
  })

  it('键不在四语名单内、或混合了非语言键，都不算（避免劫持普通 JSON 设置）', () => {
    expect(isI18nDict({ name: '支付宝', image: '/a.png', note: '' })).toBe(false)
    expect(isI18nDict({ zh: 'x', logo: 'y' })).toBe(false)
    expect(isI18nDict({ en: 'x', EN: 'y' })).toBe(false)
  })

  it('值不是字符串 / null 的不算', () => {
    expect(isI18nDict({ zh: 1 })).toBe(false)
    expect(isI18nDict({ zh: { nested: 'x' } })).toBe(false)
  })
})

describe('后端真实默认值确实是 locale dict（判定在线上数据上成立）', () => {
  /** 抠出某组 return 段里指定键的对象字面量。 */
  function backendDefaultEntry(fn: string, key: string): string {
    expect(existsSync(GROUPS_PY), `${GROUPS_PY} 不存在`).toBe(true)
    const raw = readFileSync(GROUPS_PY, 'utf8')
    const start = raw.indexOf(`def ${fn}()`)
    expect(start, `找不到 ${fn}`).toBeGreaterThan(-1)
    const end = raw.indexOf('\ndef ', start + 1)
    const seg = raw.slice(start, end === -1 ? raw.length : end)
    const keyAt = seg.search(new RegExp(`^\\s*"${key}":\\s*\\{`, 'm'))
    expect(keyAt, `${fn} 里找不到 ${key} 的对象默认值`).toBeGreaterThan(-1)
    const braceAt = seg.indexOf('{', keyAt)
    const closeAt = seg.indexOf('}', braceAt)
    return seg.slice(braceAt, closeAt + 1)
  }

  it.each([
    ['_default_hero', 'cta_text'],
    ['_default_donate', 'title'],
    ['_default_donate', 'description']
  ])('%s().%s 是含 zh/en 的对象', (fn, key) => {
    const literal = backendDefaultEntry(fn, key)
    expect(literal).toMatch(/"zh"\s*:/)
    expect(literal).toMatch(/"en"\s*:/)
    // 形状与 isI18nDict 的判定一致（键集合可以只是子集）
    const parsed = JSON.parse(literal.replace(/([{,]\s*)([a-zA-Z_]+)\s*:/g, '$1"$2":').replace(/'/g, '"'))
    expect(isI18nDict(parsed)).toBe(true)
  })
})

describe('settings.vue：i18n 分支接线', () => {
  const src = readFileSync(SETTINGS_VUE, 'utf8')

  it('FieldSchema 支持 i18n 类型', () => {
    expect(src).toMatch(/type:\s*'string'\s*\|\s*'number'\s*\|\s*'boolean'\s*\|\s*'color'\s*\|\s*'json'\s*\|\s*'i18n'/)
  })

  it('判定必须早于通用 object → json 分支（顺序错了就永远走不到）', () => {
    const i18nAt = src.indexOf('if (isI18nDict(value)) return')
    const jsonAt = src.indexOf('type: \'json\'')
    expect(i18nAt, 'inferSchema 里没有 isI18nDict(value) 判定').toBeGreaterThan(-1)
    expect(jsonAt, '找不到通用 json 分支').toBeGreaterThan(-1)
    expect(i18nAt).toBeLessThan(jsonAt)
  })

  it('缺失值的兜底也识别 i18n（默认值必须是四语 dict，不能是 {}）', () => {
    expect(src).toContain('if (isI18nDict(d)) return')
    for (const anchor of ['hero:', 'donate:']) {
      const at = src.indexOf(`\n    ${anchor}`)
      expect(at, `找不到 ${anchor} 默认值`).toBeGreaterThan(-1)
    }
    expect(src).toMatch(/cta_text:\s*\{\s*\.\.\.EMPTY_I18N_DICT\s*\}/)
    expect(src).toContain('title: { ...EMPTY_I18N_DICT }, description: { ...EMPTY_I18N_DICT }')
  })

  it('i18n 分支渲染 I18nTabsEditor，并把编辑结果写回本组字段', () => {
    expect(src).toContain('schema.type === \'i18n\'')
    expect(src).toContain('<I18nTabsEditor')
    expect(src).toContain(':model-value="i18nValueOf(key)"')
    expect(src).toContain('setI18nValue(key, v)')
    expect(src).toMatch(/import I18nTabsEditor from '~~\/components\/admin\/I18nTabsEditor\.vue'/)
  })

  it('i18n 字段不得再走 JSON 文本域', () => {
    // parseJsonInput 只服务真正的数组/对象设置；i18n 分支的 model-value 不是 stringifyJson
    const i18nBlock = src.slice(src.indexOf('schema.type === \'i18n\''), src.indexOf('schema.type === \'number\''))
    expect(i18nBlock).not.toContain('parseJsonInput')
    expect(i18nBlock).not.toContain('stringifyJson')
  })
})
