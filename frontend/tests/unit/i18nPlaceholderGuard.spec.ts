import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * 占位符守卫：ja / zh_Hant 曾经把 `[JA]:English` / `[繁]:English` 这种批量生成的
 * 占位字面量直接发布到前台（留言板、关于页、搜索结果、动态流都会原样显示）。
 * 断言读的是**磁盘上的 JSON 原文**，不做 i18n runtime 解析，所以新增语言文件
 * 或有人贴回占位串都会立刻红。
 */
const LOCALE_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../../i18n/locales')
const LOCALES = ['zh', 'en', 'ja', 'zh_Hant']

describe('i18n locale files', () => {
  for (const locale of LOCALES) {
    it(`${locale}.json carries no [xx]: placeholder literals`, () => {
      const raw = readFileSync(resolve(LOCALE_DIR, `${locale}.json`), 'utf8')
      const hits = raw.match(/\[(JA|繁|EN|中)\]:/g) ?? []
      expect(hits, `${locale}.json 残留占位符：${hits.length} 处`).toEqual([])
    })

    it(`${locale}.json is valid JSON with a nav block`, () => {
      const parsed = JSON.parse(readFileSync(resolve(LOCALE_DIR, `${locale}.json`), 'utf8'))
      expect(parsed.nav).toBeTruthy()
      // 导航必须有「动态」入口（deliverable：全站导航增加动态页）
      expect(typeof parsed.nav.activity).toBe('string')
      expect(parsed.nav.activity).not.toMatch(/\[/)
    })
  }
})
