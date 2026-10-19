import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * 站点里出现过的真实缺陷：模板写了 t('captcha.refresh')，但四语语言包都没有这个键，
 * 读屏软件于是把原始键名 "captcha.refresh" 念了出来（aria-label 里没有兜底默认值时，
 * vue-i18n 直接回显 key）。带兜底的 t(key, '默认文案') 同样有问题：默认值是中文，
 * 日语/英语访客看到的就是中文句子。所以这里把"字面量 key 必须四语齐全"钉成契约。
 */
const ROOT = process.cwd()
const LOCALES = ['zh', 'en', 'ja', 'zh_Hant']
const SKIP_DIRS = new Set(['node_modules', '.nuxt', '.output', 'dist', 'tests', 'themes', 'i18n'])

function flatten(obj: Record<string, unknown>, prefix = ''): Set<string> {
  const out = new Set<string>()
  for (const key of Object.keys(obj)) {
    const path = prefix ? `${prefix}.${key}` : key
    out.add(path)
    const value = obj[key]
    if (value && typeof value === 'object') {
      for (const nested of flatten(value as Record<string, unknown>, path)) out.add(nested)
    }
  }
  return out
}

function localeKeys(code: string): Set<string> {
  return flatten(JSON.parse(readFileSync(resolve(ROOT, 'i18n/locales', `${code}.json`), 'utf8')) as Record<string, unknown>)
}

function sourceFiles(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (SKIP_DIRS.has(name)) continue
    const full = join(dir, name)
    if (statSync(full).isDirectory()) sourceFiles(full, acc)
    else if (/\.(vue|ts)$/.test(name)) acc.push(full)
  }
  return acc
}

/**
 * 注释里的 t('x.y') 不是消费点（文档型说明会大量出现），必须先剥掉再计数。
 * \b 用来排除 import('highlight.js') 这类尾部恰好是 t( 的其它函数。
 */
function literalI18nKeys(file: string): string[] {
  const text = readFileSync(file, 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n')
    .filter(line => !/^\s*(\/\/|#|\*)/.test(line))
    .join('\n')
  const re = /\b(?:t|te)\(\s*(['"])([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)\1/g
  const keys: string[] = []
  for (const match of text.matchAll(re)) {
    if (match[2]) keys.push(match[2])
  }
  return keys
}

const keysByLocale = new Map(LOCALES.map(code => [code, localeKeys(code)]))
const usedKeys = new Map<string, string>()
for (const file of sourceFiles(ROOT)) {
  for (const key of literalI18nKeys(relative(ROOT, file))) {
    if (!usedKeys.has(key)) usedKeys.set(key, relative(ROOT, file))
  }
}

describe('字面量 i18n key 必须在四语语言包里都存在', () => {
  it('清点到的 key 数量达到基线（扫不到东西说明遍历规则坏了，测试本身失去意义）', () => {
    expect(usedKeys.size).toBeGreaterThan(600)
  })

  it('每个 t()/te() 字面量 key 都存在于 zh/en/ja/zh_Hant 四个语言包', () => {
    const missing: string[] = []
    for (const [key, where] of usedKeys) {
      for (const code of LOCALES) {
        if (!keysByLocale.get(code)!.has(key)) missing.push(`${key} (${code}) <- ${where}`)
      }
    }
    expect(missing, `语言包缺键会让 UI 吐出原始 key 或兜底中文：\n${missing.join('\n')}`).toEqual([])
  })

  it('四个语言包的扁平键集完全一致（不允许某语言先加键）', () => {
    const base = keysByLocale.get('zh')!
    for (const code of LOCALES.filter(c => c !== 'zh')) {
      const other = keysByLocale.get(code)!
      expect([...base].filter(k => !other.has(k)), `${code} 缺少的键`).toEqual([])
      expect([...other].filter(k => !base.has(k)), `${code} 多出的键`).toEqual([])
    }
  })
})
