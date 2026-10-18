/**
 * 后台首页轮播落地契约（2026-10-18）。
 *
 * 钉三件静态可判、运行时容易静默失效的事：
 * 1. 五个 /admin/hero/slides 口都有真实调用点——本仓出过"封装存在但没人点"的假阳性，
 *    光看 useAdminManage 有没有导出判不出来，必须看页面有没有调。
 * 2. 多语言字段提交前必须过 JSON.stringify：后端 HeroSlide* 是 extra=forbid + `title: str | None`，
 *    直接发字典会 422，而 422 的报错文案对用户只有一句"参数错误"，很难反查到这一层。
 * 3. media_type 只允许 image：首页只有背景图层，video/youtube 存得进去却永不渲染。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const pagePath = 'pages/admin/content/hero.vue'
const menuPath = 'config/admin-menu.ts'
const managePath = 'composables/useAdminManage.ts'

const page = existsSync(resolve(process.cwd(), pagePath))
  ? readFileSync(resolve(process.cwd(), pagePath), 'utf8')
  : ''
const menu = readFileSync(resolve(process.cwd(), menuPath), 'utf8')
const manage = readFileSync(resolve(process.cwd(), managePath), 'utf8')

describe('后台首页轮播管理页', () => {
  it('页面存在且已登记进侧栏菜单（防死链 / 防做出来进不去）', () => {
    expect(page, 'pages/admin/content/hero.vue 必须存在').not.toBe('')
    expect(menu).toMatch(/path: '\/admin\/content\/hero'/)
  })

  it('五个管理端点全部有真实调用点', () => {
    for (const fn of [
      'fetchAdminHeroSlides',
      'createAdminHeroSlide',
      'updateAdminHeroSlide',
      'deleteAdminHeroSlide',
      'toggleAdminHeroSlide'
    ]) {
      expect(manage, `wrapper ${fn} 必须打在 /admin/hero/slides 上`)
        .toMatch(new RegExp(`${fn}[\\s\\S]{0,160}/admin/hero/slides`))
      expect(page, `页面必须调用 ${fn}()`).toContain(`${fn}(`)
    }
  })

  it('多语言字段以 JSON 字符串提交，空字典提交 null', () => {
    expect(page).toMatch(/function fromDict/)
    expect(page).toContain('JSON.stringify(values)')
    expect(page, '四语全空必须回 null，否则首页把空串当成"有文案"顶掉兜底标题')
      .toMatch(/return hasText \? JSON\.stringify\(values\) : null/)
  })

  it('只提供 image 媒体类型（首页无视频渲染面）', () => {
    expect(page).toMatch(/media_type: 'image'/)
    expect(page, '不得给出 video/youtube 选项').not.toMatch(/value:\s*'(video|youtube)'/)
  })

  it('失败提示单源：页面 catch 内不得二次弹错（双 toast 是回归）', () => {
    const catchBlocks = page.match(/catch \(err\) \{[\s\S]{0,200}?\n *\}/g) ?? []
    expect(catchBlocks.length, '写路径必须有 catch 兜住状态').toBeGreaterThan(0)
    for (const block of catchBlocks) {
      expect(block, 'catch 内只允许 console.error，错误 toast 由 apiFetch 统一发')
        .not.toMatch(/toast\.(error|warning)\(/)
    }
  })
})
