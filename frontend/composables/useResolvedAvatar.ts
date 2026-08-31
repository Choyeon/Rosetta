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
 *   - 空值时返回 DiceBear identicon 确定性默认头像（按 seed 生成；若未传 seed，
 *     则按浏览器当前用户名/站点名生成可复现的 seed）。
 */

import { computed } from 'vue'

export interface ResolveAvatarOptions {
  /** 生成默认头像的确定性种子（建议：username / email） */
  seed?: string
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

function defaultSeedFromEnv(): string {
  // SSR 环境无 window，直接用固定 token，保持可复现
  const host = (typeof window !== 'undefined' ? window.location.hostname : 'rosetta') || 'rosetta'
  return fnv1aHash(`${host}|guest|${Date.now().toString().slice(0, -6)}`)
}

/**
 * DiceBear 9.x 公开端点：全球 CDN 稳定、免 key、SVG 矢量、体积小。
 * 选择 identicon：简洁、类似 GitHub 默认头像风格、性别中立。
 */
function dicebearAvatarUrl(seed: string): string {
  const s = encodeURIComponent(seed || defaultSeedFromEnv())
  return `https://api.dicebear.com/9.x/identicon/svg?seed=${s}&backgroundType=gradientLinear&backgroundRotation=0,360`
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

  // 全部候选失败 → 使用 DiceBear 生成稳定的默认头像（不再返回 ''）
  const seed = opts.seed && String(opts.seed).trim() ? fnv1aHash(String(opts.seed).trim()) : defaultSeedFromEnv()
  return dicebearAvatarUrl(seed)
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
