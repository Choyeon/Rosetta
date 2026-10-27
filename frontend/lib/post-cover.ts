/**
 * postCover —— 文章封面取值的单一来源。
 *
 * 文章未设置 cover_image 时，**前台展示面**（列表卡片 / 详情页头图 / 相似文章缩略图）
 * 回落到按文章标识派生的 picsum seed 随机图：
 *   https://picsum.photos/seed/<seed>/<w>/<h>
 * seed 由文章自身稳定标识派生（FNV-1a），因此
 *   · 同一篇文章每次渲染（含 SSR 首字节与客户端 hydrate）拿到完全相同的图，
 *     不会出现换图闪烁，也不会水合 mismatch；
 *   · 不同 seed ⇒ 不同图，整站列表不会九张一模一样。
 * picsum 不可达（限流/被墙）时由 `<img @error>` 兜底切到站内渐变占位封面
 * （/placeholder-covers/<1..6>.svg，同 seed 同槽位），页面不会碎图。
 * **SEO 面不受影响**：og:image / twitter:image / JSON-LD 走 postShareImage，
 * 无封面仍是站内 `public/og-default.png`，绝不把外链交给分享爬虫。
 * 只读派生，绝不写回 DB：管理端表单仍以真实 cover_image 为准。
 */

/** 站内外链随机图的 seed 基址（仅展示面使用）。 */
const PICSUM_BASE = 'https://picsum.photos/seed'

/** 站内兜底封面槽位数，须与 public/placeholder-covers/ 的文件数一致（postCover.spec 钉住）。 */
export const PLACEHOLDER_COVER_SLOTS = 6
const PLACEHOLDER_BASE = '/placeholder-covers'

/** 列表卡片尺寸：3:2，够清晰又不至于给首页塞九张 1200px 大图。 */
export const POST_COVER_CARD = { width: 640, height: 427 } as const
/** 详情页头图尺寸。 */
export const POST_COVER_DETAIL = { width: 1200, height: 800 } as const
/** 详情页 21:9 头图横幅（picsum 按显示比例出图，不再拉 3:2 再裁掉 36% 高度）。 */
export const POST_COVER_BANNER = { width: 1200, height: 514 } as const

interface CoverSource {
  id?: number | string | null
  slug?: string | null
  cover_image?: string | null
  coverImage?: string | null
}

/**
 * FNV-1a 32 位：把任意字符串压成短小、稳定、纯 ASCII 的 seed 片段。
 * 用于 slug 为中文（URL 里还得再编码）或列表未带 id 的兜底场景。
 */
function hashSeed(input: string): string {
  let h = 0x811c9dc5
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h.toString(36)
}

function buildSeed(post: CoverSource): string {
  const rawId = post.id
  if (rawId !== undefined && rawId !== null && String(rawId).trim() !== '') {
    return `rosetta-post-${String(rawId).trim()}`
  }
  const slug = String(post.slug ?? '').trim()
  // 与后端 URL 规范一致：先解一层百分号，让 %E4%B8%AD 与「中」得到同一 seed。
  let normalized = slug
  if (normalized) {
    try {
      normalized = decodeURIComponent(normalized)
    } catch {
      // 非法百分号序列：按原样参与 hash，不影响确定性
    }
  }
  return normalized
    ? `rosetta-slug-${hashSeed(normalized)}`
    : `rosetta-anon-${hashSeed(JSON.stringify([post.cover_image, post.slug]))}`
}

/** 展示面默认封面：按文章标识派生的 picsum seed 随机图（篇篇不同、同篇恒定）。 */
export function defaultPostCover(
  post: CoverSource,
  size: { width: number, height: number } = POST_COVER_CARD
): string {
  const seed = buildSeed(post)
  return `${PICSUM_BASE}/${seed}/${size.width}/${size.height}`
}

/** 站内渐变占位封面（picsum 不可达时的 <img @error> 兜底；同 seed 同槽位）。 */
export function placeholderPostCover(post: CoverSource): string {
  const seed = buildSeed(post)
  const slot = (Number.parseInt(hashSeed(seed).slice(0, 6), 36) % PLACEHOLDER_COVER_SLOTS) + 1
  return `${PLACEHOLDER_BASE}/${slot}.svg`
}

/**
 * `<img @error>` 兜底：外链随机图加载失败时切成站内占位封面，只切一次。
 * post 必须与产出当前 src 的是同一标识（槽位同 seed 同图），否则等于换图闪烁。
 * 数据未到时（null/undefined）按 anon seed 回落，与 postCoverUrl 的空态同轨。
 */
export function handlePostCoverError(event: Event, post: CoverSource | null | undefined): void {
  const img = event.target as HTMLImageElement | null
  if (!img || img.dataset.coverFallback === 'true') return
  img.dataset.coverFallback = 'true'
  img.src = placeholderPostCover(post ?? {})
}

/** 有封面用封面，没封面用展示面默认随机图。 */
export function postCoverUrl(
  post: CoverSource | null | undefined,
  size: { width: number, height: number } = POST_COVER_CARD
): string {
  if (!post) return ''
  const explicit = post.cover_image || post.coverImage || ''
  if (explicit.trim()) return explicit.trim()
  return defaultPostCover(post, size)
}

/**
 * 社交分享兜底图。必须是**位图**：X / Facebook / LinkedIn / Slack / Discord
 * 的卡片解析器不渲染 SVG，把 `/placeholder-covers/<n>.svg` 塞进 og:image
 * 的结果是一张空白预览图，而 `public/og-default.png` 才是为此准备的资源
 * （AGENTS.md §2.3.4：站点级兜底图是 PNG，且不得回落到站外服务）。
 */
export const OG_FALLBACK_IMAGE = '/og-default.png'

/**
 * 分享图取值（og:image / twitter:image / JSON-LD 专用，与页面 hero 的 coverImage 分开）。
 *
 * 展示面回落是 picsum 外链（被墙即无图）与 SVG 占位（爬虫不渲染），两者都不能进
 * 分享卡片，因此无封面一律回落到站点级 PNG，绝不外链。
 */
export function postShareImage(post: CoverSource | null | undefined): string {
  const explicit = (post?.cover_image || post?.coverImage || '').trim()
  return explicit || OG_FALLBACK_IMAGE
}
