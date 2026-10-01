/**
 * useResolvedAvatar
 * -----------------
 * 全站统一的头像 URL 解析 + 规范化工具。
 *
 * 背景：后端不同接口返回的头像字段不一致：
 *   1) authStore.user / users/me → avatar 字段可能是：绝对 URL (http...)、相对路径
 *      (/uploads/avatar.png)、或需要再代理的外部 URL (github.com/xxx.png)
 *   2) admin 用户列表 (AdminUserRow) → 提供 resolved_avatar_url（后端已
 *      通过 /api/media/avatar?src=... 代理过）
 *   3) 评论作者 / 活跃评论者 → avatar 可能是 null 或裸 URL
 *
 * 输出：
 *   - 返回适合直接填进 <AvatarImage :src="..." /> 的最终字符串 URL
 *   - 空值时返回本地生成的确定性默认头像（内联 SVG data URI：按 seed 取色的渐变 +
 *     首字母），零网络请求、SSR/CSR 一致；未传 seed 时落到固定站点 seed（不再掺时间）。
 */

import { computed } from 'vue'

export interface ResolveAvatarOptions {
  /** 生成默认头像的确定性种子（建议：username / email） */
  seed?: string
  /** 默认头像上叠的首字母来源（通常传昵称/用户名）；不传则只画渐变底 */
  label?: string
}

const KNOWN_ABSOLUTE_RE = /^https?:\/\//i
const API_MEDIA_RE = /^\/api\/media\//i

/**
 * 明显无效/占位的头像 URL 黑名单：
 * - IANA 保留域名 (example.com / example.org)
 * - RFC 2606 测试域名 (test / invalid / localhost)
 * - 空的占位协议 (data: 之前已经在下方分支处理，所以不列在此)
 */
const BAD_HOST_RE = /(^|\.)(example\.(com|org|net)|invalid|localhost|test|example\.edu)(:\d+)?$/i

function _isInvalidAvatarAbsoluteUrl(v: string): boolean {
  if (!KNOWN_ABSOLUTE_RE.test(v)) return false
  try {
    const u = new URL(v)
    if (BAD_HOST_RE.test(u.hostname)) return true
    // 空路径或者 avatar.png 这种 RDF/占位文件名，通常是 mock_data 里遗留
    const path = u.pathname.toLowerCase()
    if (path === '' || path === '/' || path.endsWith('avatar.png')) {
      // 进一步：若 hostname 属于无效/占位域，直接判定为无效
      if (BAD_HOST_RE.test(u.hostname)) return true
    }
    // 私有 IP / 内网地址，跨域加载大多失败
    const h = u.hostname
    if (
      h === '0.0.0.0'
      || h.startsWith('127.')
      || h.startsWith('10.')
      || /^192\.168\./.test(h)
      || /^172\.(1[6-9]|2\d|3[01])\./.test(h)
      || h === '::1'
      || h.includes('[::')
    ) {
      return true
    }
    return false
  } catch {
    return true
  }
}

/** 稳定的 32bit 字符串哈希（FNV-1a），避免把用户名直接暴露在 URL 中 */
function fnv1aHash(text: string): string {
  let h = 0x811c9dc5
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h.toString(16).padStart(8, '0')
}

/**
 * 默认头像配色：由 seed 确定性推导的渐变——同一 seed 永远同一组颜色。
 * 色相取哈希前 16 bit；饱和度/亮度固定在主题友好区间（不撞纯灰、不刺眼）。
 * 该算法同时被 UserAvatar 的「加载中 / 加载失败」占位层复用，保证三种状态视觉统一。
 */
export function avatarAccent(seed?: string | null): { hue: number, from: string, to: string } {
  const raw = String(seed ?? '').trim()
  const hue = parseInt(fnv1aHash(raw || 'rosetta').slice(0, 4), 16) % 360
  return {
    hue,
    from: `hsl(${hue} 64% 58%)`,
    to: `hsl(${(hue + 42) % 360} 66% 46%)`
  }
}

/** 首字母：取第一个码点（兼容中文与 emoji 代理对）；无名字时返回空串（只画渐变底） */
export function avatarInitial(label?: string | null): string {
  const s = String(label ?? '').trim()
  if (!s) return ''
  return (Array.from(s)[0] || '').toUpperCase()
}

function _escapeXml(s: string): string {
  return s.replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`)
}

/**
 * 默认头像：内联 SVG data URI（确定性渐变 + 首字母），零网络请求。
 *
 * 为什么不再外链 DiceBear（2026-10-01）：
 * - 每个头像都要打一次 /api/media/avatar 代理（首页 25 个），首屏被外部 CDN 拖慢，
 *   外部不可用时整站默认头像一起消失；
 * - 旧实现 seed 缺失时把 Date.now() 混进 seed → SSR 与客户端算出的值不同，同一个人
 *   刷新页面头像会变，且是潜在的 hydration 不一致源；
 * - 本地生成后默认头像即时可见，且与「加载中 / 加载失败」占位同一套配色，视觉统一。
 *
 * 后端 /api/media/avatar 的 DiceBear 兜底保留：它负责「自定义/外部头像加载失败」场景。
 */
export function defaultAvatarDataUri(seed?: string | null, label?: string | null): string {
  const { from, to } = avatarAccent(seed)
  const initial = _escapeXml(avatarInitial(label))
  const text = initial
    ? `<text x="32" y="32" text-anchor="middle" dominant-baseline="central" font-family="ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif" font-size="30" font-weight="600" fill="#fff">${initial}</text>`
    : ''
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${from}"/><stop offset="1" stop-color="${to}"/></linearGradient></defs><rect width="64" height="64" rx="32" fill="url(#g)"/>${text}</svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

/**
 * 把任意来源的头像候选值规范化为最终可用 URL。
 * @param optsOrFirst    可选的 { seed } 或第一个候选值
 * @param restCandidates 剩余候选值（按优先级尝试）
 */
export function resolveAvatarUrl(
  optsOrFirst?: ResolveAvatarOptions | string | null,
  ...restCandidates: Array<string | null | undefined>
): string {
  const { public: pub } = useRuntimeConfig()
  const apiBase = (pub?.apiBase as string) || '/api'

  let opts: ResolveAvatarOptions = {}
  let candidates: Array<string | null | undefined>

  // 首参数是 { seed } 对象 → 解读为 options；否则就是候选值
  if (
    optsOrFirst != null
    && typeof optsOrFirst === 'object'
    && !Array.isArray(optsOrFirst)
    && ('seed' in optsOrFirst || Object.keys(optsOrFirst).length === 0)
  ) {
    opts = optsOrFirst as ResolveAvatarOptions
    candidates = restCandidates
  } else {
    candidates = [optsOrFirst as string | null | undefined, ...restCandidates]
  }

  for (const raw of candidates) {
    if (!raw) continue
    const v = String(raw).trim()
    if (!v || v === 'null' || v === 'undefined') continue
    if (API_MEDIA_RE.test(v)) return v
    if (KNOWN_ABSOLUTE_RE.test(v)) {
      // 无效 URL（example.com / 内网）：跳过，不尝试代理，避免 ORB
      if (_isInvalidAvatarAbsoluteUrl(v)) continue
      try {
        const encoded = btoa(unescape(encodeURIComponent(v)))
        return `${apiBase}/media/avatar?src=${encoded}&fallback=1`
      } catch {
        continue
      }
    }
    if (v.startsWith('/')) {
      if (v.startsWith('/logo/') || v.startsWith('/favicon')) return v
      return `${apiBase}${v}`
    }
    if (v.startsWith('data:')) return v
    // 未知格式的裸串（例如 "/avatar.png"）：可能是占位，跳过，不包装
  }

  // 全部候选失败 → 本地生成的确定性默认头像（零请求、SSR/CSR 完全一致）。
  // 不再外链 DiceBear：它退居后端 /api/media/avatar 的「外部头像加载失败兜底」，
  // 前端不主动为每个默认头像发起代理请求。
  return defaultAvatarDataUri(opts.seed, opts.label)
}

/**
 * composable 形式：返回 computed 响应式头像 URL。
 * 典型用法：
 *   const avatar = useResolvedAvatar(() => user.avatar, () => user.resolved_avatar_url)
 *   或指定 seed：
 *   const avatar = useResolvedAvatar({ seed: () => user.username }, () => user.avatar)
 *   template: <AvatarImage :src="avatar" />
 */
export function useResolvedAvatar(
  ...sources: Array<(() => string | null | undefined) | (() => ResolveAvatarOptions)>
) {
  return computed(() => {
    const args = sources.map(fn => fn()) as Parameters<typeof resolveAvatarUrl>
    return resolveAvatarUrl(...args)
  })
}

export default useResolvedAvatar
