import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, it, expect } from 'vitest'
import {
  defaultPostCover,
  placeholderPostCover,
  handlePostCoverError,
  postCoverUrl,
  postShareImage,
  OG_FALLBACK_IMAGE,
  POST_COVER_CARD,
  POST_COVER_DETAIL
} from '@/lib/post-cover'

describe('postCover', () => {
  it('有封面时原样返回，不改写文章自己的图', () => {
    expect(postCoverUrl({ id: 7, slug: 'x', cover_image: '/uploads/a.webp' }))
      .toBe('/uploads/a.webp')
    expect(postCoverUrl({ id: 7, slug: 'x', coverImage: 'https://cdn.example.com/b.png' }))
      .toBe('https://cdn.example.com/b.png')
  })

  it('展示面无封面时回落到按文章标识派生的 picsum seed 随机图（含请求尺寸）', () => {
    expect(postCoverUrl({ id: 7, slug: 'x' }, POST_COVER_CARD))
      .toBe('https://picsum.photos/seed/rosetta-post-7/640/427')
    expect(defaultPostCover({ id: 42 }, POST_COVER_DETAIL))
      .toBe('https://picsum.photos/seed/rosetta-post-42/1200/800')
  })

  it('同一篇文章每次调用完全一致（SSR 与 hydrate 不会换图）', () => {
    const post = { id: 123, slug: 'deep-dive' }
    const again = { id: '123', slug: 'deep-dive' }
    expect(postCoverUrl(post)).toBe(postCoverUrl(again))
  })

  it('不同文章得到不同 seed 图（50 篇不重样）', () => {
    const urls = new Set(
      Array.from({ length: 50 }, (_, i) => postCoverUrl({ id: i + 1, slug: `p${i}` }))
    )
    expect(urls.size).toBe(50)
  })

  it('站内兜底封面槽位在 1..6 内循环，文件必须真实存在（public/placeholder-covers）', () => {
    const urls = new Set(
      Array.from({ length: 60 }, (_, i) => placeholderPostCover({ id: i + 1, slug: `p${i}` }))
    )
    for (const u of urls) expect(u).toMatch(/^\/placeholder-covers\/[1-6]\.svg$/)
    for (let slot = 1; slot <= 6; slot++) {
      expect(
        existsSync(resolve(__dirname, '../../public/placeholder-covers', `${slot}.svg`))
      ).toBe(true)
    }
  })

  it('缺 id 时用 slug 兜底，且百分号编码与原文同一 seed', () => {
    const raw = postCoverUrl({ slug: '中文标题' })
    const encoded = postCoverUrl({ slug: encodeURIComponent('中文标题') })
    expect(raw).toBe(encoded)
    expect(raw).toMatch(/^https:\/\/picsum\.photos\/seed\/rosetta-slug-[0-9a-z]+\//)
  })

  it('空对象不抛错（组件在数据未到时也能渲染）', () => {
    expect(postCoverUrl(null)).toBe('')
    expect(postCoverUrl({})).toMatch(/^https:\/\/picsum\.photos\/seed\/rosetta-anon-/)
  })

  it('@error 兜底：picsum 不可达时切成同标识派生的站内占位封面，且只切一次', () => {
    const img = {
      src: 'https://picsum.photos/seed/rosetta-post-7/640/427',
      dataset: {} as Record<string, string>
    } as unknown as HTMLImageElement
    const event = { target: img } as unknown as Event
    handlePostCoverError(event, { id: 7, slug: 'x' })
    expect(img.src).toBe(placeholderPostCover({ id: 7, slug: 'x' }))
    const switched = img.src
    handlePostCoverError(event, { id: 7, slug: 'x' })
    expect(img.src).toBe(switched)
  })

  // 分享图与页面展示分开取值：og:image / twitter:image / JSON-LD 不得依赖
  // picsum 外链（被墙/限流即无图），也不得给爬虫 SVG（社交卡片是空白）。
  it('分享图：有真实封面时原样使用', () => {
    expect(postShareImage({ id: 1, cover_image: '/uploads/a.webp' })).toBe('/uploads/a.webp')
    expect(postShareImage({ id: 1, coverImage: 'https://cdn.example.com/b.png' }))
      .toBe('https://cdn.example.com/b.png')
  })

  it('分享图：无封面时回落到站点级 PNG，绝不返回外链或占位 SVG', () => {
    const share = postShareImage({ id: 1, slug: 'p1' })
    expect(share).toBe(OG_FALLBACK_IMAGE)
    expect(share).toMatch(/\.png$/)
    expect(share).not.toMatch(/placeholder-covers/)
    expect(share).not.toMatch(/picsum/)
    // 兜底图必须真实存在，否则分享卡片就是 404
    expect(existsSync(resolve(__dirname, '../../public/og-default.png'))).toBe(true)
  })

  it('分享图：空值（数据未到 / 404 页）也回落到 PNG，不抛错', () => {
    expect(postShareImage(null)).toBe(OG_FALLBACK_IMAGE)
    expect(postShareImage(undefined)).toBe(OG_FALLBACK_IMAGE)
    expect(postShareImage({ cover_image: '   ' })).toBe(OG_FALLBACK_IMAGE)
  })
})
