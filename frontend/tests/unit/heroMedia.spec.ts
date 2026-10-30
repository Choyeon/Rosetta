/**
 * 首页轮播媒体分档（批次 #233）：`lib/hero-media.ts` 的纯函数 + 两个消费面的接线断言。
 *
 * 纯函数部分要钉的是"同一地址在后端与前端得到同一结论"：YouTube ID 解析、站内路径判定、
 * 封面回落链。接线部分钉两件静态可判、运行时静默失效的事：
 *   ① 首页不再按 media_type 过滤，且 video / youtube 各有真实渲染元素；
 *   ② 后台提交的是表单当前值，媒体地址过同一道校验。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  extractYoutubeId,
  heroMediaError,
  heroThumbUrl,
  isSiteRelativeMediaUrl,
  normalizeHeroMediaType,
  youtubeEmbedUrl
} from '../../lib/hero-media'

const idx = readFileSync(resolve(process.cwd(), 'pages/index.vue'), 'utf8')
const admin = readFileSync(resolve(process.cwd(), 'pages/admin/content/hero.vue'), 'utf8')

describe('normalizeHeroMediaType', () => {
  it('三档原样返回，未知/缺失一律按 image', () => {
    expect(normalizeHeroMediaType('image')).toBe('image')
    expect(normalizeHeroMediaType('video')).toBe('video')
    expect(normalizeHeroMediaType('youtube')).toBe('youtube')
    expect(normalizeHeroMediaType(null)).toBe('image')
    expect(normalizeHeroMediaType(undefined)).toBe('image')
    expect(normalizeHeroMediaType('gif')).toBe('image')
  })
})

describe('extractYoutubeId', () => {
  it.each([
    ['dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10', 'dQw4w9WgXcQ'],
    ['https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://www.youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://www.youtube.com/live/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://www.youtube.com/v/dQw4w9WgXcQ', 'dQw4w9WgXcQ']
  ])('%s → %s', (raw, expected) => {
    expect(extractYoutubeId(raw)).toBe(expected)
  })

  it.each([
    '',
    '   ',
    'short',
    'dQw4w9WgXc', // 10 位
    'https://example.com/watch?v=dQw4w9WgXcQ',
    'https://www.youtube.com/watch',
    'javascript:alert(1)',
    'https://evil.example/youtu.be/dQw4w9WgXcQ'
  ])('拒绝 %s', (raw) => {
    expect(extractYoutubeId(raw)).toBeNull()
  })
})

describe('youtubeEmbedUrl', () => {
  it('固定拼 nocookie 域，并带上静音循环播放所需的参数', () => {
    const url = youtubeEmbedUrl('dQw4w9WgXcQ')
    expect(url?.startsWith('https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?')).toBe(true)
    const params = new URL(url!).searchParams
    expect(params.get('autoplay')).toBe('1')
    expect(params.get('mute')).toBe('1')
    expect(params.get('loop')).toBe('1')
    // loop 对单视频只在 playlist 重复自身时生效
    expect(params.get('playlist')).toBe('dQw4w9WgXcQ')
    expect(params.get('controls')).toBe('0')
  })

  it('非法 ID 不产出地址（绝不把原始串拼进 iframe src）', () => {
    expect(youtubeEmbedUrl(null)).toBeNull()
    expect(youtubeEmbedUrl('')).toBeNull()
    expect(youtubeEmbedUrl('not-an-id')).toBeNull()
    expect(youtubeEmbedUrl('https://evil.example/x')).toBeNull()
  })
})

describe('isSiteRelativeMediaUrl', () => {
  it('只认以单斜杠开头的站内路径', () => {
    expect(isSiteRelativeMediaUrl('/media/a.mp4')).toBe(true)
    expect(isSiteRelativeMediaUrl('https://cdn.example.com/a.mp4')).toBe(false)
    expect(isSiteRelativeMediaUrl('//cdn.example.com/a.mp4')).toBe(false)
    expect(isSiteRelativeMediaUrl('media/a.mp4')).toBe(false)
    expect(isSiteRelativeMediaUrl('')).toBe(false)
  })
})

describe('heroMediaError（与后端 validate_media_pair 同文案）', () => {
  it('youtube 必须解析得出 ID', () => {
    expect(heroMediaError('youtube', 'https://youtu.be/dQw4w9WgXcQ')).toBeNull()
    expect(heroMediaError('youtube', 'https://example.com/x')).toContain('YouTube')
  })

  it('video 必须站内', () => {
    expect(heroMediaError('video', '/media/a.mp4')).toBeNull()
    expect(heroMediaError('video', 'https://cdn.example.com/a.mp4')).toContain('站内')
  })

  it('image 只要求非空', () => {
    expect(heroMediaError('image', 'https://img.example.com/a.jpg')).toBeNull()
    expect(heroMediaError('image', '  ')).toContain('不能为空')
  })
})

describe('heroThumbUrl', () => {
  it('image 用 media_url，且不被历史 poster 顶掉', () => {
    expect(heroThumbUrl({ media_type: 'image', media_url: '/a.jpg', poster_url: '/stale.jpg' })).toBe('/a.jpg')
  })

  it('video 用封面，没有封面就是 null（不把视频地址塞进 <img>）', () => {
    expect(heroThumbUrl({ media_type: 'video', media_url: '/a.mp4', poster_url: '/p.jpg' })).toBe('/p.jpg')
    expect(heroThumbUrl({ media_type: 'video', media_url: '/a.mp4', poster_url: null })).toBeNull()
  })

  it('youtube 封面优先，缺省回落官方 hqdefault', () => {
    expect(heroThumbUrl({ media_type: 'youtube', media_url: 'https://youtu.be/dQw4w9WgXcQ', poster_url: '/p.jpg' }))
      .toBe('/p.jpg')
    expect(heroThumbUrl({ media_type: 'youtube', media_url: 'https://youtu.be/dQw4w9WgXcQ' }))
      .toBe('https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg')
    expect(heroThumbUrl({ media_type: 'youtube', media_url: 'not-an-id' })).toBeNull()
  })

  it('缩略图也走同一个回落链（首页 HUD 与后台列表同源）', () => {
    expect(idx).toContain('heroThumbUrl(slide)')
    expect(admin).toContain('heroThumbUrl({ media_type: form.media_type')
    expect(admin).toContain('heroThumbUrl(row as AdminHeroSlide)')
  })
})

describe('首页渲染接线', () => {
  it('视频与 iframe 都是真实元素，且不吞掉指针事件（遮罩/CTA 仍可点）', () => {
    expect(idx).toMatch(/<iframe[\s\S]{0,400}heroYoutubeEmbedUrl/)
    expect(idx).toMatch(/<video[\s\S]{0,400}heroVideoUrl/)
    expect(idx).toContain('autoplay')
    expect(idx).toContain('playsinline')
    expect(idx).toContain('pointer-events-none')
  })

  it('iframe 不可聚焦、对辅助技术隐藏（背景是装饰，语义在文案层）', () => {
    expect(idx).toMatch(/<iframe[\s\S]{0,400}tabindex="-1"[\s\S]{0,400}aria-hidden="true"/)
  })

  it('视频档必须是站内地址才会渲染（CSP media-src 只有 self）', () => {
    expect(idx).toMatch(/isSiteRelativeMediaUrl\(raw\) \? raw : ''/)
  })

  it('heroHasBg 覆盖三档，避免视频轮播掉回兜底渐变', () => {
    expect(idx).toMatch(/heroHasBg = computed\(\(\) =>\s*Boolean\(heroBgUrl\.value \|\| heroVideoUrl\.value \|\| heroYoutubeEmbedUrl\.value/)
  })
})
