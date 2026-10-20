/**
 * 首页 Hero 的移动端布局契约（静态断言，跑在 SSR 之前，不需要浏览器）。
 *
 * 这一版式子上塌过一次：HUD 是 `absolute bottom-0` 浮在同一个 `min-h-[72vh]` 之上，
 * 文案只留了固定 `pb-28`。窄屏 HUD 竖排成两块（缩略图 + 提示）后高度远超 112px，
 * 于是直接压在两个 CTA 按钮上——手机上看到的就是「hero 错乱」。
 * 现在整段是 flex 列：文案 flex-1 居中、HUD 走正常文档流贴底，结构上不可能重叠。
 *
 * 断言全部读模板文本而不是跑组件：这些是"选对了布局手段"的口径，
 * 一旦被改回绝对定位就必然红，而不必等某个视口尺寸下人眼发现。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const page = readFileSync(resolve(process.cwd(), 'pages/index.vue'), 'utf8')

/** 取出 hero section 那一段模板（从 `<section v-if="heroEnabled"` 到下一个 `</section>`）。 */
const heroBlock = page.slice(
  page.indexOf('v-if="heroEnabled"'),
  page.indexOf('data-editorial-section="pinned"')
)

describe('首页 Hero 移动端布局', () => {
  it('hero section 是 flex 列，文案与 HUD 才可能各占一段而不是叠在一起', () => {
    expect(heroBlock).toMatch(/'relative isolate overflow-hidden flex flex-col'/)
  })

  it('HUD 不得回到绝对定位（那正是压住 CTA 的那种写法）', () => {
    expect(heroBlock).not.toMatch(/class="absolute bottom-0/)
    expect(heroBlock).toMatch(/<div class="relative z-20">/)
  })

  it('文案层 flex-1 居中，纵向留白由 pb 而不是固定高度撑起', () => {
    expect(heroBlock).toMatch(/flex flex-1 items-center container/)
    expect(heroBlock).not.toMatch(/min-h-\[inherit\]/)
  })

  it('标题有窄屏降档：375px 上不能直接上 text-4xl/font-black', () => {
    expect(heroBlock).toMatch(/text-\[1\.75rem\] leading-\[1\.15\] sm:text-4xl md:text-6xl/)
    // 长中文/英文标题不能把整段撑破
    expect(heroBlock).toMatch(/\[overflow-wrap:anywhere\]/)
  })

  it('两个 CTA 的点击高度 ≥44px', () => {
    const hits = heroBlock.match(/min-h-11 items-center justify-center/g) ?? []
    expect(hits.length).toBe(2)
  })

  it('幻灯片序号浮在缩略图之上（img 曾带 z-20 把它整个盖掉）', () => {
    expect(heroBlock).toMatch(/w-full h-full object-cover transition-opacity duration-300 ease-out z-0/)
  })
})

describe('首页 Hero 动效', () => {
  it('文案切换不用 out-in：旧文案离场改绝对定位叠在原位淡出', () => {
    expect(page).not.toMatch(/name="hero-copy"\s*\n\s*mode="out-in"/)
    const style = page.slice(page.indexOf('<style scoped>'))
    expect(style).toMatch(/\.hero-copy-leave-active \{ position: absolute; inset: 0;/)
  })

  it('prefers-reduced-motion 仍然关掉这两组过渡', () => {
    const style = page.slice(page.indexOf('<style scoped>'))
    const reduced = style.slice(style.indexOf('prefers-reduced-motion'))
    expect(reduced).toMatch(/\.hero-xfade-enter-active,/)
    expect(reduced).toMatch(/\.hero-copy-enter-active,/)
    expect(reduced).toMatch(/transition: none;/)
  })
})
