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
const postsPage = readFileSync(resolve(root, 'frontend/pages/posts/index.vue'), 'utf8')

/**
 * 该符号是否由 `services/post_access` 这个单源模块导入。
 *
 * 批次 #139 起这一族还会继续加符号（锁位 `access_flags` / `post_access_flags`），
 * 整行字面量比对会在每次加位时红一次——那不是在描述"有没有复用单源"，而是在描述
 * "导入行的字符顺序恰好是什么"。所以按语句取导入清单，再判符号在里面。
 */
function importsFromPostAccess(src: string, symbol: string): boolean {
  const stmt = src.match(
    /from backend\.services\.post_access import \([\s\S]*?\)|from backend\.services\.post_access import [^\n]+/
  )
  if (!stmt) return false
  return new RegExp(`\\b${symbol}\\b`).test(stmt[0])
}

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
    // 构造点之外每一处"手搭的文章行"也必须产出三位，这个数就是那份清单：
    // 归档年/月（2）+ 我的点赞走的 _build_post_list_item（1）+ 我的文章（1）+ 阅读历史（1）。
    // 新增一个手搭出口而没补这一处＝那一族的徽标永远不亮；补了出口就得同步改这里，
    // 让"又一个读口没带位"必须在门禁响一次，而不是等到读者发现收藏里没有锁标。
    expect(flagSpreads).toBe(constructions + 5)
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
    expect(importsFromPostAccess(rankingApi, 'post_media_flags')).toBe(true)
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
    expect(importsFromPostAccess(repo, 'media_flags')).toBe(true)
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
    expect(importsFromPostAccess(seriesApi, 'media_flags')).toBe(true)
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

describe('列表按媒体档位筛选（批次 #123）', () => {
  // 徽标是"这篇带不带"，筛选是同一判据的反向用法。两处各写一遍就会分叉：
  // SQL 写成 IS NOT NULL、Python 侧是 bool(col) 时，库里一条 audio='' 的文章
  // "筛得出来却没有徽标"。所以判据必须单源，而档位取值必须进缓存键。
  it('筛选谓词单源在 services/post_access，列表口只引用它', () => {
    expect(accessSvc).toContain('def media_presence_filter(kind: str | None)')
    expect(blogApi).toContain('media_filter = media_presence_filter(media)')
    // 只钉「把单源谓词接进查询」这个动作，不绑定局部变量名
    // （P2-9 把 query 改名为 base 曾让 toContain('query = query.where(media_filter)') 失效）。
    expect(blogApi).toMatch(/\b\w+ = \w+\.where\(media_filter\)/)
    // 在 api 里另写一份 IS NOT NULL 形态的判据＝两判据分叉的开始
    expect(blogApi).not.toMatch(/Post\.audio\.isnot|Post\.video\.isnot/)
  })

  it('媒体档位进列表缓存键（少了判别位＝筛选结果与全站列表共用一个键位）', () => {
    expect(blogApi).toContain('f"m{media or \'all\'}"')
    // 参数在签名与建键调用两处都得到场
    expect(blogApi).toMatch(/media: str \| None = Query\(/)
    expect(blogApi).toMatch(/sort_mode,\s+media,\s+\)/)
  })

  it('后端白名单 ⇔ 页面下拉档位，两个方向相等', () => {
    const declared = accessSvc.match(/MEDIA_FILTER_KINDS = \(([^)]*)\)/)?.[1] ?? ''
    const kinds = Array
      .from(declared.matchAll(/"([^"]+)"/g), m => m[1])
      .filter((v): v is string => typeof v === 'string')
    expect([...kinds].sort()).toEqual(['audio', 'video'])
    for (const kind of kinds) {
      expect(postsPage, kind).toContain(`<SelectItem value="${kind}">`)
      // 反向：页面不得摆出一个后端不认的档位
      expect(declared, kind).toContain(`"${kind}"`)
    }
    expect(postsPage).not.toContain('<SelectItem value="embed">')
  })

  it('页面按白名单收 URL 值、只发选中的档位，并纳入清除与地址栏同步', () => {
    expect(postsPage).toMatch(/rawMedia === 'audio' \|\| rawMedia === 'video' \? rawMedia : ALL_MEDIA/)
    expect(postsPage).toContain(
      'media: selectedMedia.value !== ALL_MEDIA ? selectedMedia.value : undefined'
    )
    expect(postsPage).toContain(
      'if (selectedMedia.value !== ALL_MEDIA) q.media = selectedMedia.value'
    )
    // 「清除筛选」漏掉这一档＝点一次"清除"仍留在筛过的集合里，按钮在撒谎
    expect(postsPage).toContain('selectedMedia.value = ALL_MEDIA')
    expect(postsPage).toContain('|| selectedMedia.value !== ALL_MEDIA')
  })

  it('四语都有筛选文案', () => {
    for (const locale of ['zh', 'en', 'ja', 'zh_Hant']) {
      const text = readFileSync(resolve(root, `frontend/i18n/locales/${locale}.json`), 'utf8')
      for (const key of ['selectMedia', 'allMedia', 'mediaAudio', 'mediaVideo']) {
        expect(text, `${locale}.${key}`).toContain(`"${key}"`)
      }
    }
  })
})

describe('登录态四档与相关文章卡（批次 #140）', () => {
  const accountPage = readFileSync(resolve(root, 'frontend/pages/account/index.vue'), 'utf8')
  const detailPage = readFileSync(resolve(root, 'frontend/pages/posts/[slug].vue'), 'utf8')
  const favorites = readFileSync(resolve(root, 'frontend/composables/useFavorites.ts'), 'utf8')
  const favoriteApi = readFileSync(resolve(root, 'backend/api/favorite.py'), 'utf8')

  it('账号页三档各挂一次媒体徽标并声明三位', () => {
    expect((accountPage.match(/<PostMediaFlags :post=/g) ?? []).length).toBe(3)
    expect((accountPage.match(/<PostReadingTime :post=/g) ?? []).length).toBe(3)
    expect((accountPage.match(/<PostLockBadge :post=/g) ?? []).length).toBe(3)
    expect(accountPage).toContain('import PostMediaFlags from \'~~/components/PostMediaFlags.vue\'')
    expect(accountPage).toContain('has_audio?: boolean')
  })

  it('详情页相关推荐卡挂一次三兄弟（载荷早就有三位，缺的是渲染）', () => {
    expect(detailPage).toContain('<PostMediaFlags :post="sp.raw" />')
    expect(detailPage).toContain('<PostLockBadge :post="sp.raw" />')
    expect(detailPage).toContain('<PostReadingTime :post="sp.raw" />')
  })

  it('收藏口复用单源产出点，不自己写一遍三位 dict', () => {
    expect(favoriteApi).toContain('**post_media_flags(post),')
    expect(favoriteApi).toContain('**post_access_flags(post),')
    expect(favoriteApi).not.toContain('"has_audio": bool(')
    expect(favorites).toContain('has_audio?: boolean')
  })
})
