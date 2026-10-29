/**
 * 前台公开面不得消费后台文案。
 *
 * 这类泄漏在界面上"看起来正常"——中文读者读到的仍是「文章列表加载失败」，
 * 但同一句文案挂在 `admin.*` 命名空间下，它的语义是"后台文章列表"。实测泄漏面有两条：
 *   1) `/` 的空态显示 `admin.posts.empty`=「暂无文章，点击下方按钮开始创作。」，
 *      访客在首页被指引去点一个首页根本不存在的按钮；
 *   2) 分类 / 标签 / 作者 / 活动 / 归档 / 系列 / 热门 / 文章列表的失败块统一读
 *      `admin.posts.loadFailed`，后台一旦改文案，前台跟着变成后台口径。
 * 修法是把公开面收拢到 `error.loadFailed` + `common.noData`，并加一条静态守卫：
 * 公开面（pages/** 与 components/** 去掉 admin 子树，加上前台布局）里出现 `t('admin.` 即红。
 *
 * 第二条守卫顺带把"四语齐全"钉住：公开面里 `t('a.b')` 这种字面量键必须在四个
 * locale JSON 里都能解析——缺一个语言时 vue-i18n 回落到 key 本身，
 * 页面上出现的是 `categories.title` 这样的裸键而构建与 lint 都不会报。
 */

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const LOCALES = ['zh', 'en', 'ja', 'zh_Hant'] as const

const dicts = Object.fromEntries(
  LOCALES.map(l => [l, JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${l}.json`), 'utf-8'))])
) as Record<string, Record<string, unknown>>

function lookup(dict: Record<string, unknown>, key: string): unknown {
  return key.split('.').reduce<unknown>((acc, part) => {
    if (acc && typeof acc === 'object') return (acc as Record<string, unknown>)[part]
    return undefined
  }, dict)
}

function walkVue(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      if (entry === 'node_modules') continue
      walkVue(full, out)
    } else if (full.endsWith('.vue')) {
      out.push(full)
    }
  }
  return out
}

/** 公开面文件集：pages 与 components 去掉 admin 子树，再补上前台布局。 */
function publicSurfaces(): string[] {
  const files = [
    ...walkVue(resolve(ROOT, 'pages')).filter(f => !relative(ROOT, f).replace(/\\/g, '/').startsWith('pages/admin')),
    ...walkVue(resolve(ROOT, 'components')).filter(f => !relative(ROOT, f).replace(/\\/g, '/').startsWith('components/admin')),
    resolve(ROOT, 'layouts/default.vue')
  ]
  return files
}

const T_CALL = /\bt\(\s*'([a-zA-Z0-9_.]+)'/g

describe('公开面与 i18n 命名空间', () => {
  it('公开面不消费 admin.* 文案', () => {
    const offenders: string[] = []
    for (const file of publicSurfaces()) {
      const src = readFileSync(file, 'utf-8')
      for (const m of src.matchAll(T_CALL)) {
        const key = m[1] ?? ''
        if (key.startsWith('admin.')) offenders.push(`${relative(ROOT, file)}: ${key}`)
      }
    }
    expect(offenders).toEqual([])
  })

  it('公开面用的每个字面量键在四语里都能解析', () => {
    const missing: string[] = []
    for (const file of publicSurfaces()) {
      const src = readFileSync(file, 'utf-8')
      for (const m of src.matchAll(T_CALL)) {
        const key = m[1] ?? ''
        if (!key.includes('.')) continue
        for (const locale of LOCALES) {
          if (lookup(dicts[locale]!, key) === undefined) {
            missing.push(`${relative(ROOT, file)}: ${locale} 缺 ${key}`)
          }
        }
      }
    }
    expect(missing).toEqual([])
  })

  it('通用失败文案与空态文案是公开面自己的键', () => {
    for (const locale of LOCALES) {
      expect(lookup(dicts[locale]!, 'error.loadFailed'), `${locale} 缺 error.loadFailed`).toBeTruthy()
      expect(lookup(dicts[locale]!, 'common.noData'), `${locale} 缺 common.noData`).toBeTruthy()
    }
    // 列表页的失败块必须真的用上它（否则键成了死键，下一轮又会有人接回 admin.posts.loadFailed）
    for (const file of ['pages/categories/index.vue', 'pages/tags/index.vue', 'pages/posts/index.vue']) {
      const src = readFileSync(resolve(ROOT, file), 'utf-8')
      expect(src, `${file} 未使用 error.loadFailed`).toContain(`t('error.loadFailed')`)
    }
  })
})
