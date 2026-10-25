/**
 * postCover —— 文章封面取值的单一来源。
 *
 * 文章未设置 cover_image 时，回落到**站内**渐变占位封面：
 *   /placeholder-covers/<1..6>.svg
 * 槽位由文章自身稳定标识派生，因此
 *   · 同一篇文章每次渲染（含 SSR 首字节与客户端 hydrate）拿到完全相同的图，
 *     不会出现换图闪烁；
 *   · 不同 seed ⇒ 不同槽位，整站列表不会出现九张一模一样的封面。
 * 不再回落到 picsum 外链：og:image / twitter:image 依赖外部服务（限流或被墙即无图），
 * 且站内 /public 资源走 nginx 一年强缓存，LCP 与分享卡片都不再跨域冷连接。
 * 只读派生，绝不写回 DB：管理端表单仍以真实 cover_image 为准。
 */

/** 占位封面槽位数，须与 public/placeholder-covers/ 的文件数一致（postCover.spec 钉住）。 */
export const PLACEHOLDER_COVER_SLOTS = 6
const PLACEHOLDER_BASE = '/placeholder-covers'

/** 列表卡片尺寸：3:2，够清晰又不至于给首页塞九张 1200px 大图。 */
export const POST_COVER_CARD = { width: 640, height: 427 } as const
/** 详情页头图尺寸。 */
export const POST_COVER_DETAIL = { width: 1200, height: 800 } as const

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

/** 站内占位封面 URL（确定性，篇篇不同；宽高固定 1200×800，渲染侧按 CSS 缩放）。 */
export function defaultPostCover(
  post: CoverSource,
  _size: { width: number, height: number } = POST_COVER_CARD
): string {
  const seed = buildSeed(post)
  const slot = (Number.parseInt(hashSeed(seed).slice(0, 6), 36) % PLACEHOLDER_COVER_SLOTS) + 1
  return `${PLACEHOLDER_BASE}/${slot}.svg`
}

/** 有封面用封面，没封面用站内占位封面。 */
export function postCoverUrl(
  post: CoverSource | null | undefined,
  size: { width: number, height: number } = POST_COVER_CARD
): string {
  if (!post) return ''
  const explicit = post.cover_image || post.coverImage || ''
  if (explicit.trim()) return explicit.trim()
  return defaultPostCover(post, size)
}
