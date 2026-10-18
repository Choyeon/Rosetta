/**
 * 曾经"只进库不进页面"的开关消费点契约。
 *
 * 表现过的 bug：后台设置页有输入框/开关，保存后 GET /api/settings/<group> 里值是对的，
 * 前台却永远不读它——用户判定为"设置不生效"，而代码里既没有报错也没有兜底，
 * 只能靠 grep 全仓才发现。这里钉住每一项，防止再次退化成死字段：
 * - hero.bg_image / hero.bg_gradient → pages/index.vue 的 hero section 背景
 * - hero.enable                      → pages/index.vue 整段 hero 的 v-if
 * - footer.show_back_to_top          → layouts/default.vue 的回到顶部按钮
 * - footer.show_social_links         → components/AppFooter.vue 的 socialLinks 计算属性
 * - footer.police_icp_number         → components/AppFooter.vue 两套页脚的备案行
 * - features.enable_share_buttons    → pages/posts/[slug].vue 的分享条
 * - enable_bing_wallpaper            → pages/login.vue + pages/register.vue 的壁纸拉取与切壁纸控件
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const homePage = readFileSync(resolve(process.cwd(), 'pages/index.vue'), 'utf8')
const loginPage = readFileSync(resolve(process.cwd(), 'pages/login.vue'), 'utf8')
const registerPage = readFileSync(resolve(process.cwd(), 'pages/register.vue'), 'utf8')
const defaultLayout = readFileSync(resolve(process.cwd(), 'layouts/default.vue'), 'utf8')
const postPage = readFileSync(resolve(process.cwd(), 'pages/posts/[slug].vue'), 'utf8')
const footerComp = readFileSync(resolve(process.cwd(), 'components/AppFooter.vue'), 'utf8')

describe('站点设置开关必须有真实消费点', () => {
  it('首页 hero 背景读取 hero.bg_image 与 hero.bg_gradient', () => {
    expect(homePage).toContain('site.hero.value.bg_image')
    expect(homePage).toContain('site.hero.value.bg_gradient')
    expect(homePage, '自配背景必须能压过轮播图，否则配了等于没配')
      .toMatch(/heroBgImage\.value\s*\|\|\s*heroSlideMedia\.value/)
    expect(homePage, '写进 style 的 URL 必须先过白名单正则').toMatch(/HERO_BG_URL_RE\.test/)
  })

  it('首页横幅内容源是 /hero/slides，不再请求 Bing 每日壁纸', () => {
    expect(homePage).toContain('useAPI<HeroSlideApi[]>(\'/hero/slides\'')
    expect(homePage, '首页引入 useBingWallpaper 会把首屏绑到站外图片（壁纸只服务登录/注册页）')
      .not.toContain('useBingWallpaper')
    expect(homePage, '轮播必须有真实切换面，否则只有第一张能用')
      .toMatch(/function selectHeroSlide/)
  })

  it('登录/注册页尊重 enable_bing_wallpaper 开关', () => {
    for (const [name, src] of [['login.vue', loginPage], ['register.vue', registerPage]] as const) {
      expect(src, `${name} 必须从 /api/config 的 publicConfig 读这一项`)
        .toContain('publicConfig?.enable_bing_wallpaper')
      expect(src, `${name} 关开关后不得再打壁纸请求（否则站外图片仍然出现在登录页）`)
        .toMatch(/!isMinimalAuth\.value && bingWallpaperEnabled\.value/)
      expect(src, `${name} 的切壁纸控件要一起隐藏，不留没有内容的可点外壳`)
        .toMatch(/v-if="bingWallpaperEnabled"[\s\S]{0,200}pointer-events-auto/)
    }
  })

  it('页脚「回到顶部」读取 footer.show_back_to_top', () => {
    expect(defaultLayout).toContain('site.footer.value.show_back_to_top')
    expect(defaultLayout).toMatch(/aria-label="t\('a11y\.backToTop'\)"/)
  })

  it('文章分享条读取 features.enable_share_buttons', () => {
    expect(postPage).toContain('site.features.value.enable_share_buttons')
    expect(postPage, '分享地址必须走 canonical 同款前缀算法，不能拼 window.location')
      .toContain('applyLocalePrefix(seoPostPath.value')
    expect(postPage).toMatch(/rel="noopener noreferrer"/)
    expect(postPage, 'Clipboard API 在 http 下会 reject，必须有 textarea 兜底，否则按钮形同虚设')
      .toContain('document.execCommand')
  })

  it('首页「启用 Hero」读取 hero.enable', () => {
    expect(homePage).toContain('site.hero.value.enable !== false')
    expect(homePage, '关掉开关必须整段不渲染，而不是留个 visibility:hidden 的假开关')
      .toMatch(/<section\s+v-if="heroEnabled"/)
    expect(homePage, 'hero 不渲染时不该再请求每日壁纸').toContain('heroEnabled.value')
  })

  it('页脚社交链接读取 footer.show_social_links', () => {
    expect(footerComp).toContain('site.footer.value.show_social_links === false')
  })

  it('页脚渲染 footer.police_icp_number（公安备案号）', () => {
    expect(footerComp).toContain('f.police_icp_number')
    expect(footerComp, '两套页脚骨架都要显示备案号').toMatch(/siteConfig\.police_icp_number/)
  })
})
