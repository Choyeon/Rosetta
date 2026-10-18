/**
 * /sponsor 全站 500 的回归钉（2026-10-18）。
 *
 * 现场：SSR 响应 `SyntaxError: 26`，vue-i18n 的 I18nErrorCodes[26] = MUST_BE_CALL_SETUP_TOP。
 * 起因是 useSite 的 `pickI18n` / `hero` 在 **computed 函数体内部**调用 `useI18n()`。
 * computed 是惰性的：页面把站点文案派生值作为 Ref 交给 useSeo() 后，unhead 在 SSR 收尾期
 * （以及任何 watch 回调里）第一次求值时已经没有组件实例，useI18n() 当场抛错 → 整页 500。
 * 首页当时没炸只是因为它的 hero computed 先被模板求值过一次（实例还在），属于顺序运气。
 *
 * 口径：useSite 里所有 i18n 访问必须走 safeI18n()——实例内取 composer，取不到回落到
 * useNuxtApp().$i18n，再取不到返回空串（空串让 pickI18n 走 dict 自带的 zh/en 兜底）。
 * 与 useApi.ts / useBingWallpaper.ts 里已记录的同一坑注释同轨。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const siteSrc = readFileSync(resolve(process.cwd(), 'composables/useSite.ts'), 'utf8')

describe('useSite 的 i18n 访问不得依赖组件实例', () => {
  it('useSite.ts 内不再有任何裸 useI18n() 调用（全部走 safeI18n）', () => {
    expect(siteSrc, 'useSite.ts 不得直接调用 useI18n()').not.toMatch(/=\s*useI18n\(\)/)
    expect(siteSrc).toMatch(/function safeI18n\(/)
  })

  it('safeI18n 三层回落：实例 composer → 全局 $i18n → 空串，且用 getCurrentInstance 预判', () => {
    expect(siteSrc).toMatch(/getCurrentInstance\(\)/)
    expect(siteSrc).toMatch(/useNuxtApp\(\)\.\$i18n/)
    expect(siteSrc, '兜底分支必须返回空 locale，让 pickI18n 走 dict 兜底而不是抛错').toMatch(/locale:\s*''/)
  })

  it('hero / pickI18n 这两个 computed 内站点文案口都改用 safeI18n', () => {
    const destructures = [...siteSrc.matchAll(/const \{[^}]*\} = (safeI18n|useI18n)\(\)/g)].map(m => m[1])
    expect(destructures.length, 'hero 与 pickI18n 各一处').toBeGreaterThanOrEqual(2)
    expect(destructures, '不允许残留 useI18n').toEqual(destructures.map(() => 'safeI18n'))
  })
})
