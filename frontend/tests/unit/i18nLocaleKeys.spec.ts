/**
 * i18n 语言包三条守卫：键集一致、无孤儿键、无缺键。
 *
 * 为什么用源码文本扫描而不是跑起来断言：语言包是**打进客户端 bundle** 的
 * （nuxt.config 里 i18n 没开 lazy，四语 JSON 全量加载）。本仓实测有 576 个键在任何
 * 源码里都找不到字面量 —— 也就是约 93 KB / 单语言约 22 KB 的死文案，每个访客都要
 * 下载并解析一次。这类"改了 .vue 忘了删 JSON"的残留不会报错，只会静默变大。
 *
 * 三条断言各对应一类真实缺陷：
 *   ① 四语键集必须逐键相同 —— 少一个键时 vue-i18n 会按 fallbackLocale(en) 兜底，
 *      繁体/日文页面混进英文文案，且没有任何报警；
 *   ② 键必须有消费点 —— 除动态拼装的命名空间（见 PROTECT）外，孤儿键即死负载；
 *   ③ 源码里引用的字面量键必须存在 —— 缺键的表现是页面直接渲染裸 key
 *      （`footer.home` 这种），页脚为此专门写了四语兜底表。
 */
import { describe, it, expect } from 'vitest'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import process from 'node:process'

const ROOT = process.cwd().replace(/[\\/]$/, '')
const LOCALE_FILES = ['zh', 'en', 'ja', 'zh_Hant']
const SOURCE_DIRS = [
  'pages',
  'components',
  'composables',
  'lib',
  'server',
  'stores',
  'plugins',
  'middleware',
  'layouts',
  'app.vue',
  'error.vue',
  'nuxt.config.ts',
  'i18n.config.ts'
]
/** 动态 key 命名空间：`t(\`nav.${x}\`)` / \`account.tab${cap}\` / 页脚按 labelKey 取值，
 *  字面量不在源码里，不能按孤儿键处理。 */
const PROTECT = ['nav.', 'account.', 'activity.type_', 'footer.', 'common.']

function walkSources(): string[] {
  const out: string[] = []
  for (const entry of SOURCE_DIRS) {
    const full = `${ROOT}/${entry}`
    if (!existsSync(full)) continue
    if (statSync(full).isFile()) {
      out.push(full)
      continue
    }
    const stack = [full]
    while (stack.length) {
      const dir = stack.pop() as string
      for (const item of readdirSync(dir, { withFileTypes: true })) {
        if (item.name === 'node_modules' || item.name.startsWith('.')) continue
        const path = `${dir}/${item.name}`
        if (item.isDirectory()) stack.push(path)
        else if (/\.(vue|ts|js)$/u.test(item.name)) out.push(path)
      }
    }
  }
  return out
}

function leafKeys(obj: Record<string, unknown>, prefix = ''): Set<string> {
  const out = new Set<string>()
  for (const [key, value] of Object.entries(obj)) {
    const full = `${prefix}${key}`
    if (value && typeof value === 'object') {
      for (const nested of leafKeys(value as Record<string, unknown>, `${full}.`)) out.add(nested)
    } else out.add(full)
  }
  return out
}

const locales = Object.fromEntries(
  LOCALE_FILES.map(code => [
    code,
    leafKeys(JSON.parse(readFileSync(`${ROOT}/i18n/locales/${code}.json`, 'utf8')) as Record<string, unknown>)
  ])
)
const sources = walkSources().map(file => ({ file, text: readFileSync(file, 'utf8') }))
const blob = sources.map(s => s.text).join('\n')

describe('i18n 语言包键集', () => {
  it('四种语言的叶子键完全一致（缺一个键就会混进 fallbackLocale 的英文）', () => {
    const zh = locales.zh
    for (const code of LOCALE_FILES.slice(1)) {
      const set = locales[code]
      const missing = [...zh].filter(k => !set.has(k)).sort()
      const extra = [...set].filter(k => !zh.has(k)).sort()
      expect({ code, missing, extra }, `语言包 ${code} 与 zh 键集不一致`).toEqual({ code, missing: [], extra: [] })
    }
  })

  it('键量下限（防止整块命名空间被误删）', () => {
    expect(locales.zh.size).toBeGreaterThanOrEqual(900)
  })
})

describe('i18n 语言包不得有孤儿键', () => {
  it('除动态命名空间外，每个键都必须在源码里以字面量出现过', () => {
    const orphans = [...locales.zh]
      .filter(key => !PROTECT.some(p => key.startsWith(p)))
      .filter(key => !blob.includes(key))
      .sort()
    expect(
      orphans.slice(0, 30),
      `这 ${orphans.length} 个键没有任何消费点，却仍然打进客户端语言包，请从四语 JSON 一起删除：${orphans.join(', ')}`
    ).toEqual([])
  })
})

describe('源码引用的键必须存在', () => {
  it('t("x.y") 字面量键都能在语言包里找到', () => {
    // 只认真正的翻译调用 t(...) / $t(...)：`import(` 结尾也是 t( ，不加负向后顾会把
    // 动态 import 的模块名当成翻译键误报缺键。
    const pattern = /(?<![\w$])\$?t\(\s*['"]([a-zA-Z][\w]*\.[\w.]+)['"]/gu
    const missing = new Set<string>()
    for (const { file, text } of sources) {
      if (/i18n[\\/]locales/u.test(file)) continue
      for (const match of text.matchAll(pattern)) {
        if (!locales.zh.has(match[1])) missing.add(`${match[1]} <- ${file.replace(`${ROOT}/`, '')}`)
      }
    }
    expect([...missing].sort(), '缺键会把裸 key 渲染到页面上').toEqual([])
  })
})
