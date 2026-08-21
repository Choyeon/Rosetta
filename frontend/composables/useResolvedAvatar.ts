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
 *   - 空值时返回 ''（由 AvatarFallback 兜底）
 */

import { computed } from 'vue'

const KNOWN_ABSOLUTE_RE = /^https?:\/\//i
const API_MEDIA_RE = /^\/api\/media\//i

/**
 * 把任意来源的头像候选值规范化为最终可用 URL。
 * @param candidates 任意数量的候选值，按优先级尝试（典型：resolved 优先，再 avatar）
 */
export function resolveAvatarUrl(...candidates: Array<string | null | undefined>): string {
  const { public: pub } = useRuntimeConfig()
  const apiBase = (pub?.apiBase as string) || '/api'
  // 优先剥离 query
  for (const raw of candidates) {
    if (!raw) continue
    const v = String(raw).trim()
    if (!v || v === 'null' || v === 'undefined') continue
    // 已是代理好的 API 路径
    if (API_MEDIA_RE.test(v)) return v
    // 绝对 URL（github / gravatar / 任意站外图片）→ 通过后端 media 代理
    // 避免 mixed content + Referer 403 + Referrer-Policy 问题
    if (KNOWN_ABSOLUTE_RE.test(v)) {
      try {
        const encoded = btoa(unescape(encodeURIComponent(v)))
        return `${apiBase}/media/avatar?src=${encoded}`
      } catch {
        // btoa 编码失败（理论 Unicode 已 unescape）就原样返回
        return v
      }
    }
    // 相对路径（/uploads/avatar.png） → 拼 apiBase 前缀
    if (v.startsWith('/')) {
      // 如果看起来已经指向 static 资源 (/logo/*, /favicon.ico) 直接返回
      if (v.startsWith('/logo/') || v.startsWith('/favicon')) return v
      return `${apiBase}${v}`
    }
    // 其它：上传文件名、纯 base64 data:
    if (v.startsWith('data:')) return v
    return `${apiBase}/media/avatar?src=${btoa(unescape(encodeURIComponent(v)))}`
  }
  return ''
}

/**
 * composable 形式：返回 computed 响应式头像 URL。
 * 典型用法：
 *   const avatar = useResolvedAvatar(() => user.avatar, () => user.resolved_avatar_url)
 *   template: <AvatarImage :src="avatar" />
 */
export function useResolvedAvatar(
  ...sources: Array<() => string | null | undefined>
) {
  return computed(() => resolveAvatarUrl(...sources.map(fn => fn())))
}

export default useResolvedAvatar
