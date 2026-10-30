/**
 * donate.`enable` 是"本站不再接受捐助"的总开关，三个公开面必须同一条判据：
 *  - 后端公开设置投影 `_public_donate`（`backend/api/settings_groups.py`）清空
 *    `methods` / `sponsors` / `show_sponsors_list`；
 *  - `GET /api/sponsors`（`backend/api/core.py`）回空；
 *  - 前台 `/sponsor` 只渲染占位并输出 noindex（`pages/sponsor.vue`）。
 *
 * 曾经只有前端 noindex 与页脚入口看这个开关：关掉后收款码仍随公开设置下发、
 * 打赏名单接口照常吐数据，直接访问 /sponsor 依旧看得见收款码——运营者以为"关了"，
 * 访客看到的页面却一点没变。这里把三处一起钉住，改判据时漏一处就红。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const sponsorPage = readFileSync(resolve(ROOT, 'pages/sponsor.vue'), 'utf8')
const backendGroups = readFileSync(resolve(ROOT, '../backend/api/settings_groups.py'), 'utf8')
const backendCore = readFileSync(resolve(ROOT, '../backend/api/core.py'), 'utf8')

describe('捐助总开关 donate.enable', () => {
  it('前台 /sponsor 的收款码与打赏墙都受 enable 约束', () => {
    expect(sponsorPage).toContain('v-if="donate.enable && donate.methods.length"')
    expect(sponsorPage).toContain(
      'donate.value.enable && donate.value.show_sponsors_list && sponsors.value.length > 0'
    )
    expect(sponsorPage).toContain('noindex: sponsorEmpty')
  })

  it('公开设置投影清空 methods/sponsors，并在 get_public_settings 里应用', () => {
    expect(backendGroups).toContain('def _public_donate(group: dict) -> dict:')
    expect(backendGroups).toContain(
      'return {**group, "methods": [], "sponsors": [], "show_sponsors_list": False}'
    )
    expect(backendGroups).toContain('public["donate"] = _public_donate(public["donate"])')
  })

  it('打赏名单公开接口同时看 enable 与 show_sponsors_list', () => {
    expect(backendCore).toContain(
      'bool_of(group, "enable", True) and bool_of(group, "show_sponsors_list", True)'
    )
  })
})
