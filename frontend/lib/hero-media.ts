/**
 * 首页轮播媒体类型的唯一判定（`pages/index.vue` 渲染面 + `pages/admin/content/hero.vue` 表单共用）。
 *
 * 三档语义：
 * - `image`：`media_url` 就是一张图，铺成背景层（原有行为）。
 * - `video`：`media_url` 是**站内**视频地址（`/media/…`）。CSP `media-src` 只有
 *   `'self' blob: data:`，外链视频会被浏览器直接拦掉——写入口（后端 `validate_media_pair`）
 *   与这里都拒外链，两处必须同口径。
 * - `youtube`：`media_url` 是视频链接或裸 ID，渲染面用 privacy-enhanced 的
 *   `youtube-nocookie.com` iframe。CSP `frame-src` 只放这一个域
 *   （`backend/core/security_middleware.py::CSP_FRAME_SRCS` ↔ `deploy/nginx-site.conf`）。
 *
 * 为什么前端还要再解一次 ID：渲染侧不能信库里的字段形态（导入 ZIP 直写 ORM、直接打接口都能
 * 塞进任意串），而 iframe 的 src 会原样进 DOM。解析不出 ID 就整条退回静图/兜底背景，
 * 绝不做"把原始串拼进 iframe src"这种事。
 */

export type HeroMediaType = 'image' | 'video' | 'youtube'

const YOUTUBE_ID_RE = /^[A-Za-z0-9_-]{11}$/
const YOUTUBE_HOSTS = new Set(['youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'youtu.be'])
const YOUTUBE_PATH_PREFIXES = ['embed/', 'shorts/', 'live/', 'v/']

/** 未知/缺失一律按 image：字段缺失就整条不显示等于把首页首屏交出去赌一个字段。 */
export function normalizeHeroMediaType(raw: string | null | undefined): HeroMediaType {
  if (raw === 'video' || raw === 'youtube') return raw
  return 'image'
}

/**
 * 从裸 ID / youtu.be / watch?v= / embed / shorts / live / v 各种形态里取出 11 位 ID。
 * 与后端 `backend/schemas/hero.py::extract_youtube_id` 同口径（多认一种少认一种是两处漂移）。
 */
export function extractYoutubeId(raw: string | null | undefined): string | null {
  const value = typeof raw === 'string' ? raw.trim() : ''
  if (!value) return null
  if (YOUTUBE_ID_RE.test(value)) return value

  let parsed: URL
  try {
    // 没写协议时按 https 解析（运营者常直接粘 youtu.be/xxx）。
    parsed = new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(value) ? value : `https://${value}`)
  } catch {
    return null
  }
  if (!YOUTUBE_HOSTS.has(parsed.hostname.replace(/^www\./, ''))) return null

  const clean = (v: string | null) => (v && YOUTUBE_ID_RE.test(v) ? v : null)
  const fromQuery = clean(parsed.searchParams.get('v'))
  if (fromQuery) return fromQuery

  const segments = parsed.pathname.split('/').filter(Boolean)
  if (!segments.length) return null
  if (YOUTUBE_PATH_PREFIXES.some(prefix => parsed.pathname.startsWith(`/${prefix}`))) {
    return clean(segments[1] ?? null)
  }
  // youtu.be/<id> 与 watch/<id> 这类路径尾段
  return clean(segments[segments.length - 1] ?? null)
}

/**
 * 嵌入地址：静音 + 循环 + 隐藏控制条。轮播是装饰性背景，播放器控件会把文案 CTA 顶掉；
 * `playlist` 必须重复自己的 ID，否则 `loop=1` 对单视频不生效（YouTube 的历史行为）。
 */
export function youtubeEmbedUrl(videoId: string | null): string | null {
  if (!videoId || !YOUTUBE_ID_RE.test(videoId)) return null
  const params = new URLSearchParams({
    autoplay: '1',
    mute: '1',
    loop: '1',
    playlist: videoId,
    controls: '0',
    modestbranding: '1',
    playsinline: '1',
    rel: '0',
    iv_load_policy: '3'
  })
  return `https://www.youtube-nocookie.com/embed/${videoId}?${params.toString()}`
}

/**
 * `video` 档必须是站内地址。协议相对地址（`//host/v.mp4`）也算外链：它会被浏览器当作
 * 当前页面的协议去请求站外主机，与写死 `https://…` 等价。
 */
export function isSiteRelativeMediaUrl(raw: string | null | undefined): boolean {
  const value = typeof raw === 'string' ? raw.trim() : ''
  if (!value || value.startsWith('//')) return false
  return value.startsWith('/')
}

/**
 * 「媒体类型 ↔ 地址」的搭配校验，文案与后端 `validate_media_pair` 一一对应。
 * 后台表单在提交前先过这一道，让原因当场可见；后端仍会再拦一次（写入口不止这一个）。
 */
export function heroMediaError(mediaType: string | null | undefined, mediaUrl: string | null | undefined): string | null {
  const type = normalizeHeroMediaType(mediaType)
  const url = (mediaUrl ?? '').trim()
  if (!url) return '媒体地址不能为空'
  if (type === 'youtube') {
    return extractYoutubeId(url) === null
      ? 'YouTube 地址无法解析出视频 ID（支持 watch?v= / youtu.be / embed / shorts）'
      : null
  }
  if (type === 'video' && !isSiteRelativeMediaUrl(url)) {
    return '视频地址必须是站内路径（如 /media/xxx.mp4），外链会被 CSP 拦截'
  }
  return null
}

/**
 * 缩略图/静图：`poster_url` 优先；YouTube 回落官方 hqdefault（每个可播放视频都有）；
 * `video` 档没有 poster 就返回 null——视频文件塞进 <img> 只会得到一张碎图，
 * 缩略图按钮本身还有序号层，不显示静图也不缺信息。
 */
export function heroThumbUrl(slide: {
  media_type?: string | null
  media_url?: string | null
  poster_url?: string | null
}): string | null {
  const type = normalizeHeroMediaType(slide.media_type)
  // image 档不看 poster：那张列为视频/嵌入服务，留着历史值时不该顶掉真正的背景图。
  const poster = type === 'image' ? '' : (slide.poster_url ?? '').trim()
  if (poster) return poster
  if (type === 'image') return (slide.media_url ?? '').trim() || null
  if (type === 'youtube') {
    const id = extractYoutubeId(slide.media_url)
    return id ? `https://i.ytimg.com/vi/${id}/hqdefault.jpg` : null
  }
  return null
}
