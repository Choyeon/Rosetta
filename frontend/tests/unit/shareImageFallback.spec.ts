/**
 * 分享图回落契约（2026-10-29 线上实测缺陷）。
 *
 * 现场：全站扫描 25 条公开路由，只有文章详情页有 `og:image`。首页与所有列表页
 * （/posts、/categories、/tags、/archive、/series、/gallery…）都只有
 * `twitter:card=summary_large_image` 而没有 `og:image` / `twitter:image`：
 * 社交平台按大字卡排版却拿不到图，预览退化成纯文字。
 *
 * 根因：后台「站内默认分享图」`seo.default_og_image`（默认 /og-default.png）只被
 * 后端 RSS/SEO 端点消费，前端 useSeo 只在调用方显式传 image 时才输出分享图；
 * 首页传的是另一字段 `seo.og_image`，默认空串 → 一路空到底。
 *
 * 口径：分享图取值走 resolveShareImage（显式 → 后台默认 → 站内品牌图），
 * 任何公开页都不允许"声明大字卡却没有图"。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { resolveShareImage } from '../../composables/useSeo'

const ROOT = resolve(__dirname, '..', '..')
const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf8')
const site = readFileSync(resolve(ROOT, 'composables/useSite.ts'), 'utf8')

describe('resolveShareImage 三层取值', () => {
  it('显式图片优先于后台默认', () => {
    expect(resolveShareImage('/uploads/cover.png', '/og-default.png')).toBe('/uploads/cover.png')
  })

  it('无显式图片时用后台默认分享图', () => {
    expect(resolveShareImage('', '/custom-share.png')).toBe('/custom-share.png')
  })

  it('两者都空时回落站内品牌图（OOBE / 分组未下发）', () => {
    expect(resolveShareImage('', '')).toBe('/og-default.png')
  })

  it('空白串视作未配置', () => {
    expect(resolveShareImage('   ', '  ')).toBe('/og-default.png')
  })

  it('绝对外链原样透传（后台可配 CDN 图）', () => {
    expect(resolveShareImage('', 'https://cdn.example.com/og.png')).toBe('https://cdn.example.com/og.png')
  })
})

describe('接线：useSeo 消费 default_og_image，useSite 暴露它', () => {
  it('useSeo 的 _image 走 resolveShareImage 且读 default_og_image', () => {
    expect(seo).toContain('resolveShareImage(')
    expect(seo).toContain('default_og_image')
    expect(seo).toContain('OG_FALLBACK_IMAGE')
  })

  it('useSite 的 seo 分组带上 default_og_image 兜底', () => {
    expect(site).toMatch(/default_og_image:\s*\(state\.value\.publicConfig\?\.default_og_image as string\) \|\| '\/og-default\.png'/)
  })

  it('image 存在时 alt 必有值（回落站点名，不输出空 alt）', () => {
    expect(seo).toContain('const imageAlt = _imageAlt.value || siteName.value')
  })
})
