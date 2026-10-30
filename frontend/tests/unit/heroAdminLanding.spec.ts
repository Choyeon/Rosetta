/**
 * 后台首页轮播落地契约（2026-10-18）。
 *
 * 钉三件静态可判、运行时容易静默失效的事：
 * 1. 五个 /admin/hero/slides 口都有真实调用点——本仓出过"封装存在但没人点"的假阳性，
 *    光看 useAdminManage 有没有导出判不出来，必须看页面有没有调。
 * 2. 多语言字段提交前必须过 JSON.stringify：后端 HeroSlide* 是 extra=forbid + `title: str | None`，
 *    直接发字典会 422，而 422 的报错文案对用户只有一句"参数错误"，很难反查到这一层。
 * 3. media_type 三档都要能发出（image / video / youtube），且提交前过与后端同源的搭配校验；
 *    图片档显式清空 `poster_url`，否则切回图片时历史封面会顶掉背景图。
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

  it('三档媒体类型都能选、都真的提交', () => {
    for (const value of ['image', 'video', 'youtube']) {
      expect(page, `缺 ${value} 选项`).toMatch(new RegExp(`value: '${value}'`))
    }
    // 表单默认值允许是 image（新建时的合理起点），但提交载荷里必须是当前值
    const payloadBlock = page.slice(
      page.indexOf('const payload: AdminHeroSlidePayload'),
      page.indexOf('saving.value = true')
    )
    expect(payloadBlock).toContain('media_type: form.media_type')
    expect(payloadBlock, '载荷里不得再写死 image').not.toMatch(/media_type: 'image'/)
  })

  it('媒体地址提交前过与后端同源的搭配校验', () => {
    expect(page).toContain('heroMediaError(form.media_type, form.media_url)')
  })

  it('封面只在非图片档提交，图片档显式写 null（避免历史值顶掉背景图）', () => {
    expect(page).toMatch(/poster_url: form\.media_type === 'image' \? null/)
    expect(page).toContain('form.poster_url')
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
