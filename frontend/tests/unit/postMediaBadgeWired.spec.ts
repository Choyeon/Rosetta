/**
 * 列表卡片「本文含音频 / 本文含视频」徽标的接线契约（批次 #120）。
 *
 * 后端列表口带出 `has_audio` / `has_video` / `has_embed` 三位存在性，卡片消费它们。
 * 三条反向断言各自挡一次真实事故：
 * - 只读存在性、**不读地址**：地址进列表载荷等于把媒体文件名摊给更多缓存与消费方（详情口才回）。
 * - 每个变体都挂一次：PostCard 有三个变体（default / compact / feature），漏一个就是
 *   "首页有徽标、列表页没有"这种没人报的缺陷。
 * - 后端构造点数 == 媒体位产出点数：`PostListItemLocalized` 有四个手写构造点，
 *   批次 #118 的"创建口漏三列"就是这个形状（按接口断言在 pytest 侧，这里按源码对账）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '..', '..', '..')
const card = readFileSync(resolve(root, 'frontend/components/PostCard.vue'), 'utf8')
const flags = readFileSync(resolve(root, 'frontend/components/PostMediaFlags.vue'), 'utf8')
const apiTypes = readFileSync(resolve(root, 'frontend/types/api.ts'), 'utf8')
const blogApi = readFileSync(resolve(root, 'backend/api/blog.py'), 'utf8')
const schemas = readFileSync(resolve(root, 'backend/schemas/__init__.py'), 'utf8')

describe('列表媒体徽标的消费面', () => {
  it('徽标只读存在性三位，不读媒体地址', () => {
    expect(flags).toContain('props.post.has_audio')
    expect(flags).toContain('props.post.has_video')
    expect(flags).toContain('props.post.has_embed')
    // 站内视频与 YouTube 合成一个"有画面"位：读者的问题只有一个
    expect(flags).toMatch(/has_video \|\| props\.post\.has_embed/)
    expect(flags).not.toMatch(/post\.(audio|video_url)\b/)
  })

  it('三个变体各挂一次，图标带可读文案', () => {
    expect((card.match(/<PostMediaFlags :post="post" \/>/g) ?? []).length).toBe(3)
    expect(card).toContain('import PostMediaFlags from \'~~/components/PostMediaFlags.vue\'')
    expect((flags.match(/t\('post\.hasAudio'\)/g) ?? []).length).toBeGreaterThan(0)
    expect((flags.match(/t\('post\.hasVideo'\)/g) ?? []).length).toBeGreaterThan(0)
    // 图标本身 aria-hidden，文案给 sr-only：只有 title 等于键盘/读屏用户拿不到
    expect((flags.match(/class="sr-only"/g) ?? []).length).toBe(2)
  })

  it('前端类型允许这三位缺席（旧载荷与详情口都不带）', () => {
    for (const key of ['has_audio', 'has_video', 'has_embed']) {
      expect(apiTypes).toContain(`${key}?: boolean`)
    }
  })

  it('四语都有文案', () => {
    for (const locale of ['zh', 'en', 'ja', 'zh_Hant']) {
      const text = readFileSync(resolve(root, `frontend/i18n/locales/${locale}.json`), 'utf8')
      expect(text, locale).toContain('"hasAudio"')
      expect(text, locale).toContain('"hasVideo"')
    }
  })
})

describe('后端列表投影的构造点对账', () => {
  it('每个 PostListItemLocalized 构造点都产出媒体三位', () => {
    const constructions = (blogApi.match(/PostListItemLocalized\(/g) ?? []).length
    const flagSpreads = (blogApi.match(/\*\*_media_flags\(post\),/g) ?? []).length
    expect(constructions).toBe(4)
    expect(flagSpreads).toBe(constructions)
  })

  it('模型里这三个键都带默认值（旧缓存载荷不得因缺必填整口 500）', () => {
    const body = schemas.slice(
      schemas.indexOf('class PostListItemLocalized('),
      schemas.indexOf('class ArchivePostItem(')
    )
    for (const key of ['has_audio', 'has_video', 'has_embed']) {
      expect(body).toContain(`${key}: bool = False`)
    }
  })
})
