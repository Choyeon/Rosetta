/**
 * 文章级音视频（批次 #118）：`lib/post-media.ts` 的纯函数 + 两个消费面的接线断言。
 *
 * 这一族此前的形状是「只有列、没有四段」：模型里有 audio / video / video_url，
 * 写口不收、响应不带、后台没格子、前台没播放器。接通之后最容易静默失效的是两处：
 *   ① 详情页把库里的原始串直接拼进 `<iframe src>`（那等于把任意站外页面嵌进文章页，
 *      也等于 CSP frame-src 形同虚设）；
 *   ② 编辑器只回填不发送（或只发送不回填）——前者改了等于没改，后者改一次标题就清掉音轨。
 * 两条都能在源码层判死，所以钉成静态断言。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { internalMediaSrc, postMediaErrors, youtubePlayerSrc } from '../../lib/post-media'

const ROOT = process.cwd()
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8')
const detail = read('pages/posts/[slug].vue')
const form = read('components/admin/PostForm.vue')
const types = read('types/api.ts')

describe('internalMediaSrc', () => {
  it.each([
    '/media/2026/03/a.mp3',
    '/media/a.mp4',
    '  /media/a.webm  ',
    '/uploads/x.ogg'
  ])('接受站内路径 %s', (raw) => {
    expect(internalMediaSrc(raw)).toBe(raw.trim())
  })

  it.each([
    '',
    '   ',
    null,
    undefined,
    'media/a.mp3',
    'https://cdn.example.com/a.mp4',
    'http://cdn.example.com/a.mp3',
    '//cdn.example.com/a.mp4',
    'javascript:alert(1)'
  ])('拒绝 %s（回空串＝整条不渲染）', (raw) => {
    expect(internalMediaSrc(raw)).toBe('')
  })
})

describe('youtubePlayerSrc', () => {
  it('只用解析出的 11 位 ID 拼 youtube-nocookie 嵌入', () => {
    expect(youtubePlayerSrc('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10')).toBe(
      'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?rel=0&playsinline=1'
    )
    expect(youtubePlayerSrc('https://youtu.be/dQw4w9WgXcQ')).toContain('/embed/dQw4w9WgXcQ')
  })

  it.each([
    '',
    null,
    undefined,
    'https://player.bilibili.com/player.html?aid=1',
    'https://evil.example/youtu.be/dQw4w9WgXcQ',
    '/media/clip.mp4'
  ])('解析不出 ID 就回空串，绝不退化成裸地址：%s', (raw) => {
    expect(youtubePlayerSrc(raw)).toBe('')
  })
})

describe('postMediaErrors', () => {
  it('三格全空没有错误（清空是合法操作）', () => {
    expect(postMediaErrors({})).toEqual({})
    expect(postMediaErrors({ audio: '', video: '  ', video_url: '' })).toEqual({})
  })

  it('外链音视频与非 YouTube 嵌入各报各的字段', () => {
    const errors = postMediaErrors({
      audio: 'https://cdn.example.com/a.mp3',
      video: '//cdn.example.com/a.mp4',
      video_url: 'https://example.com/watch?v=1'
    })
    expect(Object.keys(errors).sort()).toEqual(['audio', 'video', 'video_url'])
  })

  it('合规值不报错', () => {
    expect(
      postMediaErrors({
        audio: '/media/a.mp3',
        video: '/media/a.mp4',
        video_url: 'https://youtu.be/dQw4w9WgXcQ'
      })
    ).toEqual({})
  })
})

describe('详情页消费面', () => {
  it('从 lib/post-media 取值，三个源各一条 computed', () => {
    expect(detail).toContain('~~/lib/post-media')
    expect(detail).toContain('internalMediaSrc(post.value?.audio)')
    expect(detail).toContain('internalMediaSrc(post.value?.video)')
    expect(detail).toContain('youtubePlayerSrc(post.value?.video_url)')
  })

  it('audio / video / iframe 三个真实元素绑定的是取值后的源', () => {
    const block = detail.match(/v-if="postAudioSrc \|\| postVideoSrc \|\| postEmbedSrc"[\s\S]*?<\/div>/)?.[0] ?? ''
    expect(block, '找不到文章级音视频块').not.toBe('')
    expect(block).toContain('<audio')
    expect(block).toContain('<video')
    expect(block).toContain('<iframe')
    expect(block).toContain(':src="postAudioSrc"')
    expect(block).toContain(':src="postVideoSrc"')
    expect(block).toContain(':src="postEmbedSrc"')
  })

  it('播放器按"读文章"的代价加载：metadata 预载、不自动播、视频内联', () => {
    const block = detail.match(/v-if="postAudioSrc \|\| postVideoSrc \|\| postEmbedSrc"[\s\S]*?<\/div>/)?.[0] ?? ''
    // 一进页面就下整条媒体＝把首屏带宽花在一个可能根本不播的元素上（audio 还会抢跑网络队列）
    expect((block.match(/preload="metadata"/g) ?? []).length).toBe(2)
    // iOS Safari 没有 playsinline 会弹成全屏播放器，文章页的阅读上下文整块丢掉
    expect(block).toContain('playsinline')
    expect(block).not.toMatch(/autoplay/)
    expect(block).toContain('loading="lazy"')
  })

  it('库里的原始串不得直接进 src / srcdoc（iframe 只吃解析出的 ID）', () => {
    expect(detail).not.toMatch(/:src="post(\.value)?\??\.(audio|video|video_url)"/)
    expect(detail).not.toContain('srcdoc')
  })

  it('嵌入块带 title（iframe 无可读文本时辅助技术只剩一个空白区）', () => {
    const block = detail.match(/v-if="postEmbedSrc"[\s\S]*?\/>/)?.[0] ?? ''
    expect(block).toContain(':title=')
  })
})

describe('后台编辑器接线', () => {
  it('表单状态、回填、载荷三处都有这三个键', () => {
    for (const key of ['audio', 'video', 'video_url']) {
      expect(form, `表单初始状态缺 ${key}`).toMatch(new RegExp(`^\\s{2}${key}: ''`, 'm'))
      expect(form, `/edit 未回填 ${key}（改一次标题就会把它清掉）`).toContain(`form.${key} = data.${key} ?? ''`)
      expect(form, `载荷未发送 ${key}（键不在 PUT 体里＝永远删不掉）`).toContain(
        `${key}: form.${key}.trim() || null`
      )
    }
  })

  it('提交前过同一道校验，错误显示在字段上', () => {
    expect(form).toContain('~~/lib/post-media')
    expect(form).toContain('postMediaErrors(form)')
    for (const key of ['audio', 'video', 'video_url']) {
      expect(form).toContain(`mediaErrors.${key}`)
    }
  })

  it('三个输入框各有 id 与 v-model', () => {
    for (const id of ['post-form-audio', 'post-form-video', 'post-form-video-url']) {
      expect(form, `后台缺字段 ${id}`).toContain(`id="${id}"`)
    }
  })
})

describe('类型声明', () => {
  it('Post 与 PostCreate 都允许这三个可空键（清空后库里是 null）', () => {
    for (const key of ['audio', 'video', 'video_url']) {
      const matches = types.match(new RegExp(`\\b${key}\\?: string \\| null`, 'g'))
      // 读侧（Post）与写侧（PostCreate）各一条：只写一半＝类型层面就发不出这个字段
      expect(matches, `${key} 需读写两侧都在，实测 ${matches?.length ?? 0} 处`).toHaveLength(2)
    }
  })
})
