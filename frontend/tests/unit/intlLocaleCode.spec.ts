/**
 * `Intl.*` / `toLocale*` 的入参必须是 BCP-47 标签，不能直接喂 i18n 语言码。
 *
 * 实测（本地 dev + 生产构建）：`new Intl.DateTimeFormat('zh_Hant')` 抛
 * `RangeError: Incorrect locale information provided`（下划线不是合法 BCP-47），
 * 而这段跑在 `/archive/<年>/<月>` 的 setup 里 → `/zh_Hant/archive/2026/10`
 * 整页渲染成 200 空壳（<title> 只剩站点名、h1=0），en/ja/zh 三语正常。
 * 四个语言码里只有 `zh_Hant` 带下划线，所以这类缺陷只在这一个语言下出现。
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { extname, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { HREFLANG_MAP, toBcp47Locale } from '../../composables/useSeo'

const ROOT = resolve(__dirname, '..', '..')

describe('toBcp47Locale', () => {
  it.each(['zh', 'en', 'ja', 'zh_Hant'])('%s 映射出的标签 Intl 能接受', (code) => {
    const tag = toBcp47Locale(code)
    expect(tag).toBe(HREFLANG_MAP[code])
    expect(() => new Intl.DateTimeFormat(tag)).not.toThrow()
  })

  it('裸语言码不能直接喂 Intl（zh_Hant 会抛 RangeError，这正是要防的坑）', () => {
    expect(toBcp47Locale('zh_Hant')).toBe('zh-Hant')
    expect(() => new Intl.DateTimeFormat('zh_Hant')).toThrow(RangeError)
  })

  it('未知语言码按下划线换连字符兜底，空值走默认语言', () => {
    expect(toBcp47Locale('pt_BR')).toBe('pt-BR')
    expect(toBcp47Locale(undefined)).toBe(HREFLANG_MAP.zh)
    expect(toBcp47Locale('')).toBe(HREFLANG_MAP.zh)
  })
})

describe('源码里没有把裸语言码交给 Intl', () => {
  const CALL_RE = /(?:Intl\.(?:DateTimeFormat|NumberFormat)|toLocaleDateString|toLocaleTimeString|toLocaleString)\(\s*locale\.value\b/g

  const walk = (dir: string, acc: string[] = []): string[] => {
    for (const entry of readdirSync(resolve(ROOT, dir))) {
      const rel = `${dir}/${entry}`
      if (statSync(resolve(ROOT, rel)).isDirectory()) {
        walk(rel, acc)
        continue
      }
      if (['.vue', '.ts'].includes(extname(entry))) acc.push(rel)
    }
    return acc
  }

  const files = [...walk('pages'), ...walk('components'), ...walk('layouts'), ...walk('composables')]

  it.each(files)('%s', (rel) => {
    const src = readFileSync(resolve(ROOT, rel), 'utf-8')
    const hits = [...src.matchAll(CALL_RE)].map(m => m[0])
    expect(hits, `${rel} 直接用了 locale.value；先过 toBcp47Locale()，否则 zh_Hant 会抛 RangeError`).toEqual([])
  })
})
