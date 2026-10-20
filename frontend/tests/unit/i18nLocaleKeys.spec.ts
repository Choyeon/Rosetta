/**
 * i18n 四条守卫：键集一致、无孤儿键、无缺键、公开面不得写死中文可访问性名称。
 *
 * 为什么用源码文本扫描而不是跑起来断言：语言包是**打进客户端 bundle** 的
 * （nuxt.config 里 i18n 没开 lazy，四语 JSON 全量加载）。本仓实测有 576 个键在任何
 * 源码里都找不到字面量 —— 也就是约 93 KB / 单语言约 22 KB 的死文案，每个访客都要
 * 下载并解析一次。这类"改了 .vue 忘了删 JSON"的残留不会报错，只会静默变大。
 *
 * 四条断言各对应一类真实缺陷：
 *   ① 四语键集必须逐键相同 —— 少一个键时 vue-i18n 会按 fallbackLocale(en) 兜底，
 *      繁体/日文页面混进英文文案，且没有任何报警；
 *   ② 键必须有消费点 —— 除动态拼装的命名空间（见 PROTECT）外，孤儿键即死负载；
 *   ③ 源码里引用的字面量键必须存在 —— 缺键的表现是页面直接渲染裸 key
 *      （`footer.home` 这种），页脚为此专门写了四语兜底表；
 *   ④ 前台的 aria-label / title 不得写死中文 —— 读屏软件只念这一个来源。
 */
import { describe, it, expect } from 'vitest'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import process from 'node:process'

const ROOT = process.cwd().replace(/[\\/]$/, '')
const LOCALE_FILES = ['zh', 'en', 'ja', 'zh_Hant'] as const
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
/** 只有这三个命名空间存在 `t(反引号 + 前缀 + 变量)` 形态的动态拼装：AppFooter 的 nav.末段、
 *  account 的 tab / empty / avatarSource 三族、activity 的 type_ 前缀。它们的字面量不在
 *  源码里，不能按孤儿键处理。common. 与 footer. 曾一并豁免，实测这两个命名空间共 49 个键
 *  没有任何消费点，已从豁免名单移出并删除——全仓动态拼装点只有上述三处，可用同一扫描复核。 */
const PROTECT = ['nav.', 'account.', 'activity.type_']

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

function keysOf(code: (typeof LOCALE_FILES)[number]): Set<string> {
  return leafKeys(JSON.parse(readFileSync(`${ROOT}/i18n/locales/${code}.json`, 'utf8')) as Record<string, unknown>)
}
// 显式列出四个键：用 Object.fromEntries 推出来的是索引签名，
// noUncheckedIndexedAccess 下每个 locales.xx 都要写成可能 undefined，断言反而失真。
const locales: Record<(typeof LOCALE_FILES)[number], Set<string>> = {
  zh: keysOf('zh'),
  en: keysOf('en'),
  ja: keysOf('ja'),
  zh_Hant: keysOf('zh_Hant')
}
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
        const key = match[1]
        if (key && !locales.zh.has(key)) missing.add(`${key} <- ${file.replace(`${ROOT}/`, '')}`)
      }
    }
    expect([...missing].sort(), '缺键会把裸 key 渲染到页面上').toEqual([])
  })
})

/**
 * 公开面（前台页 + 共享组件）的可访问性名称必须是翻译键。
 * 写死中文的 `aria-label="关闭预览"` 在 en/ja/zh_Hant 下仍是简体字，而它是读屏软件
 * 唯一的播报来源，肉眼检查很容易漏。`components/ui/**` 是 shadcn 原子件、按约定保持
 * 无语言依赖（要本地化由调用方覆写 slot / aria-label），后台 admin 目录另有
 * 独立的本地化范围，两处都不在这一条断言内。
 *（注意：这段里不能写 glob 形式的 `x**／y`——`*` 紧跟 `/` 会提前闭合块注释，
 * 后面的中文会被 TS 当代码解析，lint/typecheck 一起报出看不懂的错。）
 */
describe('公开面不得写死中文可访问性名称', () => {
  it('非后台、非 ui 原子件的 aria-label / title 必须走 t()', () => {
    const pattern = /(?:^|[^:\w])(?:aria-label|title)="[^"]*[\u4e00-\u9fff]/gmu
    const offenders: string[] = []
    for (const { file, text } of sources) {
      const rel = file.replace(`${ROOT}/`, '').replace(/\\/g, '/')
      if (rel.includes('/admin/') || rel.startsWith('components/ui/')) continue
      for (const match of text.matchAll(pattern)) offenders.push(`${rel}: ${(match[0] ?? '').trim()}`)
    }
    expect(offenders.sort(), '前台 aria-label / title 写死中文，切语言不会跟着变').toEqual([])
  })
})
