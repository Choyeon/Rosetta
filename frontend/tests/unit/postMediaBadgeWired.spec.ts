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
 * - 不走那个模型的口（`/ranking/posts`、归档三面、系列目录）也必须复用同一个产出点：
 *   键名单源在 `services/post_access.py`（`media_flags` 按值 / `post_media_flags` 按 ORM 行），
 *   任何一处自己写一遍三行 dict，就等于给下一批改动留一个"这一族的徽标永远不亮"的洞。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '..', '..', '..')
const card = readFileSync(resolve(root, 'frontend/components/PostCard.vue'), 'utf8')
const flags = readFileSync(resolve(root, 'frontend/components/PostMediaFlags.vue'), 'utf8')
const apiTypes = readFileSync(resolve(root, 'frontend/types/api.ts'), 'utf8')
const blogApi = readFileSync(resolve(root, 'backend/api/blog.py'), 'utf8')
const rankingApi = readFileSync(resolve(root, 'backend/api/ranking.py'), 'utf8')
const hotPage = readFileSync(resolve(root, 'frontend/pages/posts/hot.vue'), 'utf8')
const schemas = readFileSync(resolve(root, 'backend/schemas/__init__.py'), 'utf8')
const blogReads = readFileSync(resolve(root, 'backend/schemas/blog_reads.py'), 'utf8')
const repo = readFileSync(resolve(root, 'backend/repositories/post.py'), 'utf8')
const seriesApi = readFileSync(resolve(root, 'backend/api/post_series.py'), 'utf8')
const accessSvc = readFileSync(resolve(root, 'backend/services/post_access.py'), 'utf8')
const archiveIndex = readFileSync(resolve(root, 'frontend/pages/archive/index.vue'), 'utf8')
const archiveYear = readFileSync(resolve(root, 'frontend/pages/archive/[year]/index.vue'), 'utf8')
const archiveMonth = readFileSync(resolve(root, 'frontend/pages/archive/[year]/[month].vue'), 'utf8')
const seriesPage = readFileSync(resolve(root, 'frontend/pages/series/[slug].vue'), 'utf8')

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
    const flagSpreads = (blogApi.match(/\*\*post_media_flags\(post\),/g) ?? []).length
    expect(constructions).toBe(4)
    // 4 个模型构造点 + 归档年/月两个裸 dict 构造点：产出点比构造点多 2 个是预期，
    // 少任何一处就是那一族的徽标永远不亮。
    expect(flagSpreads).toBe(constructions + 2)
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

describe('榜单口（/ranking/posts）的媒体三位', () => {
  // 这条口不经过 PostListItemLocalized：它自己拼 dict，而热门页的日/周/月/总榜
  // 四个页签把条目补齐成 PostCard 认得的形状。漏一处就是"综合榜有徽标、周期榜没有"。
  it('后端条目复用同一个产出点，不另写一份字段清单', () => {
    expect(rankingApi).toContain('from backend.services.post_access import post_media_flags')
    expect(rankingApi).toContain('**post_media_flags(p),')
    // 自己重写字段清单＝两处会漂移（批次 #118 的创建口漏三列同族）
    expect(rankingApi).not.toMatch(/"has_audio": bool\(/)
  })

  it('文档模型声明这三个键且都带默认值', () => {
    const body = rankingApi.slice(
      rankingApi.indexOf('class HotPostItemDoc('),
      rankingApi.indexOf('class HotPostsRankingResponseDoc(')
    )
    for (const key of ['has_audio', 'has_video', 'has_embed']) {
      expect(body, key).toContain(`${key}: bool = Field(False`)
    }
  })

  it('热门页把三位透传给同一套卡片渲染', () => {
    for (const key of ['has_audio', 'has_video', 'has_embed']) {
      expect(hotPage).toContain(`${key}?: boolean`)
      expect(hotPage).toContain(`${key}: row.${key} ?? false`)
    }
  })
})

describe('归档三面与系列目录的媒体三位（批次 #122）', () => {
  it('键名与取值单源在 services/post_access，且两种入口都在', () => {
    // 列投影（不实例化 Post）与 ORM 行两种形态各一个入口，否则归档/repository 就得反向 import api
    expect(accessSvc).toContain('def media_flags(*, audio, video, video_url)')
    expect(accessSvc).toContain('def post_media_flags(post: Post)')
    expect(accessSvc).toMatch(/return media_flags\(audio=post\.audio, video=post\.video, video_url=post\.video_url\)/)
  })

  it('归档仓储（列投影）点名取三列并复用 media_flags', () => {
    expect(repo).toContain('from backend.services.post_access import media_flags')
    for (const col of ['Post.audio', 'Post.video', 'Post.video_url']) {
      expect(repo, col).toContain(col)
    }
    expect(repo).toContain('**media_flags(audio=audio, video=video, video_url=video_url),')
  })

  it('归档文档模型声明这三个键且都带默认值', () => {
    const body = blogReads.slice(
      blogReads.indexOf('class ArchivePostItem('),
      blogReads.indexOf('class ArchiveMonthGroup(')
    )
    for (const key of ['has_audio', 'has_video', 'has_embed']) {
      expect(body, key).toContain(`${key}: bool = Field(False`)
    }
  })

  it('系列目录（列投影）复用 media_flags 并在文档模型声明三键', () => {
    expect(seriesApi).toContain('media_flags, publicly_listable_posts')
    expect(seriesApi).toContain('**media_flags(audio=r.audio, video=r.video, video_url=r.video_url),')
    for (const col of ['Post.audio,', 'Post.video,', 'Post.video_url,']) {
      expect(seriesApi, col).toContain(col)
    }
    const body = seriesApi.slice(
      seriesApi.indexOf('class SeriesPostItemDoc('),
      seriesApi.indexOf('class SeriesDetailDoc(')
    )
    for (const key of ['has_audio', 'has_video', 'has_embed']) {
      expect(body, key).toContain(`${key}: bool = Field(False`)
    }
  })

  it('归档三页与系列目录各渲染一次徽标，并允许三位缺席', () => {
    for (const [name, src] of [
      ['archive/index.vue', archiveIndex],
      ['archive/[year]/index.vue', archiveYear],
      ['archive/[year]/[month].vue', archiveMonth],
      ['series/[slug].vue', seriesPage]
    ] as const) {
      expect(src, name).toContain('<PostMediaFlags :post=')
      expect(src, name).toContain(
        'import PostMediaFlags from \'~~/components/PostMediaFlags.vue\''
      )
      for (const key of ['has_audio', 'has_video', 'has_embed']) {
        expect(src, `${name} ${key}`).toContain(`${key}?: boolean`)
      }
    }
  })

  it('渲染徽标的页面不得读媒体地址', () => {
    for (const src of [archiveIndex, archiveYear, archiveMonth, seriesPage, hotPage]) {
      expect(src).not.toMatch(/\.(audio|video_url)\b/)
    }
  })
})
