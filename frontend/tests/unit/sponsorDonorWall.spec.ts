/**
 * 打赏名单（donate.sponsors）全链路契约。
 *
 * 表现过的缺陷形态：`GET /api/sponsors` 读的是 site_configs 里 key='SPONSORS' 这条
 * 没有任何写入方的 KV，前台 /sponsor 也从不渲染名单——端点、旧键、页面三者互不认识，
 * 管理员在后台找不到入口，代码里也不报错。这里钉住收口后的四件事：
 * ① 后台设置页把名单提交进 donate 分组（且 sponsors 走专用编辑器，不进通用 schema）；
 * ② 后端 `_default_donate()` 的键集里必须有这两个键（否则 `_save_group` 的
 *    `if k in base` 会把提交的名单静默丢弃——写了存不进）；
 * ③ 前台 useSite().donate 输出归一化后的 sponsors 与 show_sponsors_list；
 * ④ /sponsor 页真的渲染名单，且开关关闭或名单为空时整块不出现。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(process.cwd())
const sponsorPage = readFileSync(resolve(ROOT, 'pages/sponsor.vue'), 'utf8')
const useSiteSrc = readFileSync(resolve(ROOT, 'composables/useSite.ts'), 'utf8')
const settingsPage = readFileSync(resolve(ROOT, 'pages/admin/system/settings.vue'), 'utf8')
const groupsPy = readFileSync(
  resolve(ROOT, '..', 'backend', 'api', 'settings_groups.py'),
  'utf-8'
)
const corePy = readFileSync(resolve(ROOT, '..', 'backend', 'api', 'core.py'), 'utf-8')

/** 后端 `_default_donate()` 返回体里的键名。 */
function donateDefaultKeys(): string[] {
  const body = groupsPy.match(/def _default_donate\(\) -> dict:[\s\S]*?\n {4}return \{([\s\S]*?)\n {4}\}/)
  const inner = body?.[1]
  if (!inner) throw new Error('找不到 _default_donate 的返回体——函数形态变了要同步改本测试')
  const keys: string[] = []
  for (const m of inner.matchAll(/^\s*"([a-z_]+)":/gm)) {
    if (m[1]) keys.push(m[1])
  }
  return keys
}

describe('打赏名单设置链路', () => {
  it('后端 donate 分组默认键集含 sponsors 与 show_sponsors_list', () => {
    const keys = donateDefaultKeys()
    expect(keys).toContain('sponsors')
    expect(keys, '缺这个开关等于名单无法对外关闭（公开接口会照样吐数据）')
      .toContain('show_sponsors_list')
  })

  it('设置页提交的 donate 键都在后端键集内（写了存不进的闸门）', () => {
    const uiLine = settingsPage.match(/^ {4}donate: \{(.*)\},?$/m)?.[1] ?? ''
    if (!uiLine) throw new Error('设置页默认表里找不到 donate 行——结构变了请同步本守卫')
    const uiKeys: string[] = []
    for (const m of uiLine.matchAll(/\b([A-Za-z_]\w*)\s*:/g)) {
      if (m[1]) uiKeys.push(m[1])
    }
    expect(uiKeys).toContain('sponsors')
    expect(uiKeys).toContain('show_sponsors_list')
    for (const key of uiKeys) {
      expect(donateDefaultKeys(), `donate.${key} 不在 _default_donate 键集里，会被 _save_group 丢弃`)
        .toContain(key)
    }
  })

  it('sponsors 由专用编辑器承载，不进通用 schema 渲染', () => {
    expect(settingsPage).toMatch(/donate: new Set<string>\(\['methods', 'sponsors'\]\)/)
    expect(settingsPage).toContain('function normalizeDonateSponsors')
    expect(settingsPage).toContain('donateSponsors.value = normalizeDonateSponsors')
    expect(settingsPage, '名称为空的行不该推给前台渲染')
      .toMatch(/payload\.sponsors = donateSponsors\.value\.filter\(/)
  })

  it('useSite().donate 输出归一化名单与开关', () => {
    expect(useSiteSrc).toContain('sponsors: [] as unknown[]')
    expect(useSiteSrc).toContain('show_sponsors_list: true')
    expect(useSiteSrc, '开关兜底必须是"默认展示"（后端默认 True，两边同口径）')
      .toContain('show_sponsors_list: g.show_sponsors_list !== false')
    expect(useSiteSrc).toMatch(/\.filter\(s => s\.name\)/)
  })

  it('/sponsor 页渲染打赏墙并按开关与空名单隐藏', () => {
    expect(sponsorPage).toContain('site.donate.value.sponsors')
    expect(sponsorPage, '开关与名单两判，缺一即"关了开关仍在渲染"或"空名单挂个空标题"')
      .toMatch(/show_sponsors_list && sponsors\.value\.length > 0/)
    expect(sponsorPage).toMatch(/v-if="showDonors"/)
    expect(sponsorPage).toContain('t(\'sponsor.donorTitle\')')
    expect(sponsorPage, '名单项必须是真实 DOM（{{ donor.name }} 与金额/日期），不是占位注释')
      .toMatch(/\{\{ donor\.name \}\}/)
    expect(sponsorPage).not.toMatch(/v-html="[^"]*donor/)
  })

  it('后端读口同源同一份分组值，并尊重同一个开关', () => {
    expect(corePy, '/api/sponsors 仍在读那条没有写入方的 key=SPONSORS 作为首选源')
      .toContain('read_group("donate", db)')
    expect(corePy).toContain('bool_of(group, "show_sponsors_list", True)')
    expect(groupsPy, 'donate 保存后必须清掉端点自有的 sponsors 响应缓存')
      .toMatch(/if group == "donate":[\s\S]{0,200}cache\.delete\(make_cache_key\("sponsors"\)\)/)
  })

  it('四语 locale 都有 sponsor.donorTitle', () => {
    for (const code of ['zh', 'en', 'ja', 'zh_Hant']) {
      const json = JSON.parse(
        readFileSync(resolve(ROOT, 'i18n', 'locales', `${code}.json`), 'utf-8')
      ) as { sponsor?: Record<string, string> }
      expect(json.sponsor?.donorTitle, `${code} 缺 sponsor.donorTitle`).toBeTruthy()
    }
  })
})
