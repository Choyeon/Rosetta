import { describe, it, expect } from 'vitest'
import { defaultPostCover, postCoverUrl, POST_COVER_CARD, POST_COVER_DETAIL } from '@/lib/post-cover'

describe('postCover', () => {
  it('有封面时原样返回，不改写文章自己的图', () => {
    expect(postCoverUrl({ id: 7, slug: 'x', cover_image: '/uploads/a.webp' }))
      .toBe('/uploads/a.webp')
    expect(postCoverUrl({ id: 7, slug: 'x', coverImage: 'https://cdn.example.com/b.png' }))
      .toBe('https://cdn.example.com/b.png')
  })

  it('无封面时回落到按 id 派生的 picsum seed 图', () => {
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

  it('不同文章得到不同 seed', () => {
    const urls = new Set(
      Array.from({ length: 50 }, (_, i) => postCoverUrl({ id: i + 1, slug: `p${i}` }))
    )
    expect(urls.size).toBe(50)
  })

  it('缺 id 时用 slug 兜底，且百分号编码与原文同一 seed', () => {
    const raw = postCoverUrl({ slug: '中文标题' })
    const encoded = postCoverUrl({ slug: encodeURIComponent('中文标题') })
    expect(raw).toBe(encoded)
    expect(raw).toMatch(/^https:\/\/picsum\.photos\/seed\/rosetta-slug-[0-9a-z]+\/640\/427$/)
  })

  it('空对象不抛错（组件在数据未到时也能渲染）', () => {
    expect(postCoverUrl(null)).toBe('')
    expect(postCoverUrl({})).toMatch(/^https:\/\/picsum\.photos\/seed\/rosetta-anon-/)
  })
})
