/**
 * 曾经"只进库不进页面"的三项开关的消费点契约。
 *
 * 表现过的 bug：后台设置页有输入框/开关，保存后 GET /api/settings/<group> 里值是对的，
 * 前台却永远不读它——用户判定为"设置不生效"，而代码里既没有报错也没有兜底，
 * 只能靠 grep 全仓才发现。这三项是扫描出来的存量，钉住防止再次退化成死字段：
 * - hero.bg_image / hero.bg_gradient → pages/index.vue 的 hero section 背景
 * - footer.show_back_to_top          → layouts/default.vue 的回到顶部按钮
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const homePage = readFileSync(resolve(process.cwd(), 'pages/index.vue'), 'utf8')
const defaultLayout = readFileSync(resolve(process.cwd(), 'layouts/default.vue'), 'utf8')

describe('站点设置开关必须有真实消费点', () => {
  it('首页 hero 背景读取 hero.bg_image 与 hero.bg_gradient', () => {
    expect(homePage).toContain('site.hero.value.bg_image')
    expect(homePage).toContain('site.hero.value.bg_gradient')
    expect(homePage, '自配背景必须能压过每日壁纸，否则配了等于没配')
      .toMatch(/heroBgImage\.value\s*\|\|\s*currentWallpaper\.value/)
    expect(homePage, '写进 style 的 URL 必须先过白名单正则').toMatch(/HERO_BG_URL_RE\.test/)
  })

  it('页脚「回到顶部」读取 footer.show_back_to_top', () => {
    expect(defaultLayout).toContain('site.footer.value.show_back_to_top')
    expect(defaultLayout).toMatch(/aria-label="t\('a11y\.backToTop'\)"/)
  })
})
