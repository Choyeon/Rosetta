/**
 * lib/utils —— 零 Nuxt 上下文的纯函数集合，分两段：
 * 前半是 UI 工具（cn = clsx + tailwind-merge 的 shadcn 约定；hex→HSL / WCAG 相对亮度，
 * 给 TagBadge 这类「背景色由数据决定」的组件自动挑前景色）；
 * 后半（extractApiErrorMessage / isOobeRequiredError / stableApiKey）被 useApi.ts import
 * 而不是就地实现，正是为了能被 vitest 直接断言。依赖方向恒为 useApi → utils，勿反向。
 */

import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * `nuxt.config.ts` 里 `app.head.title` 的构建期占位值（两处必须同字面量，
 * 由 tests/unit/spaShellTitle.spec.ts 双向钉住）。
 *
 * 为什么要单独认这个占位：`/login` `/register` `/search` `/account` `/admin` 是
 * 精准反选的 ssr:false 壳页，没有页面级标题，客户端 unhead 拿到的 chunk 就是这串
 * 编译期常量。标题拼接的两处权威（app.vue 的 titleTemplate、site-title.global.ts 的
 * buildTitle）若不认它，就会产出 "Rosetta · 站点名"，而后台「SEO · 页面默认标题」
 * 只活在"无标题"分支里 —— 管理员填了永远没反应（curl 实测 /login 标题恒为 Rosetta）。
 */
export const SPA_SHELL_TITLE_PLACEHOLDER = 'Rosetta'

// ====================== 展示用纯工具 ======================

/**
 * 计数 → 千分位文本，分组固定 en-US（`1,234`）。
 *
 * SSR 页里裸写 `n.toLocaleString()` 会按**各自运行环境**的默认 locale 分组：
 * 服务端出 `1,234`、德语浏览器出 `1.234`，两端文本不一致 → hydration mismatch，
 * 而且这个差异还会被该页的 swr 缓存固化成 TTL 内所有人看到的 HTML 字节。
 */
export function formatCount(value: number | null | undefined): string {
  const n = Number(value ?? 0)
  if (!Number.isFinite(n)) return '0'
  return n.toLocaleString('en-US')
}

/**
 * 字节数 → 人读尺寸（B / KB / MB / GB，1024 进制）。
 *
 * 收口前三处各有一份：两份完全相同但缺少 B 档（900 字节显示 "0.9 KB"），
 * 另一份 MB 用两位小数，与媒体库的口径互不一致。
 */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  if (bytes < 1024) return `${Math.round(bytes)} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(2)} GB`
}

// ====================== 颜色工具：全站共享（取代 PostCard / TagBadge 各自实现）======================

/**
 * 将 hex (#RRGGBB) 颜色转换为 HSL 对象。
 * 用于 TagBadge 的前景色对比度计算。
 */
export function hexToHsl(hex: string): { h: number, s: number, l: number } | null {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(String(hex).trim())
  if (!m) return null
  const r = parseInt(m[1] ?? '00', 16) / 255
  const g = parseInt(m[2] ?? '00', 16) / 255
  const b = parseInt(m[3] ?? '00', 16) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h = 0
  let s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0)
        break
      case g:
        h = (b - r) / d + 2
        break
      case b:
        h = (r - g) / d + 4
        break
    }
    h *= 60
  }
  return { h, s: s * 100, l: l * 100 }
}

// ====================== API 纯工具（供 useApi.ts 与单元测试共享） ======================

/** Rosetta 后端统一错误响应体，纯字段声明。 */
export interface ApiErrorBody {
  message?: string
  error_code?: string
  /**
   * 两种形状都真实存在，调用方不可只认一种：
   * - `{field,message,type}`：FastAPI 请求校验（RequestValidationError / main.py 包络）
   * - 裸字符串：业务侧自己拼的强度规则清单（如 `core/password_policy.validate_password`）
   */
  errors?: Array<{ field?: string, message?: string } | string>
  detail?: unknown
  [k: string]: unknown
}

/** errors[] 单项 → 可读文案；认不出形状返回空串。 */
function apiErrorItemText(item: unknown): string {
  if (typeof item === 'string') return item
  if (item && typeof item === 'object') {
    const m = (item as { message?: unknown }).message
    if (typeof m === 'string') return m
  }
  return ''
}

/**
 * 失败信封里的**全部**可读原因：`message` 在前、`errors[]` 逐条在后（去空去重）。
 *
 * 存在理由是 toast 只有一句话：密码强度这类"多条原因"的失败，只回 `message`
 * （"新密码不符合强度要求"）用户无从知道缺了大写还是缺了数字，
 * 表现即"点了没反应"。需要逐条展示的表单页走这里，不用 extractApiErrorMessage。
 */
export function extractApiErrorList(body: unknown): string[] {
  if (!body || typeof body !== 'object') return []
  const b = body as ApiErrorBody
  const out: string[] = []
  if (typeof b.message === 'string' && b.message) out.push(b.message)
  if (Array.isArray(b.errors)) {
    for (const item of b.errors) {
      const text = apiErrorItemText(item)
      if (text && !out.includes(text)) out.push(text)
    }
  }
  return out
}

/**
 * 从错误响应体提取用户可读信息，纯函数、零依赖组件上下文，直接可测。
 *
 * 优先级：message → detail → errors[0] → fallback。
 */
export function extractApiErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const b = body as ApiErrorBody
    if (typeof b.message === 'string' && b.message) return b.message
    if (typeof b.detail === 'string' && b.detail) return b.detail
    if (Array.isArray(b.errors) && b.errors.length) {
      const first = apiErrorItemText(b.errors[0])
      if (first) return first
    }
  }
  return fallback
}

/** 后端 OOBE 未完成：HTTP 503 + error_code === 'OOBE_REQUIRED'。 */
export function isOobeRequiredError(status: number, body: unknown): boolean {
  return status === 503
    && (body as ApiErrorBody | null | undefined)?.error_code === 'OOBE_REQUIRED'
}

/**
 * 生成 useFetch 的稳定缓存 key：
 *  - 只依赖相对路径 + query 参数（剥离 baseURL 影响），解决 SSR ↔ Client 两端缓存不命中问题
 *  - object 类型 query 值会被 JSON 序列化，保证哈希稳定性
 *  - 相同 key/value 不同输入顺序 → 仍可能不同（URLSearchParams 行为），调用者需保证顺序确定性
 */
export function stableApiKey(url: string | (() => string), query?: Record<string, unknown>): string {
  const raw = typeof url === 'function'
    ? '__fn__' + url.toString().slice(0, 80).replace(/\s+/g, '')
    : String(url)
  try {
    const qs = query
      ? '::' + new URLSearchParams(
        Object.fromEntries(
          Object.entries(query).map(([k, v]) => [k, typeof v === 'object' ? JSON.stringify(v) : String(v)])
        ) as unknown as Record<string, string>
      ).toString()
      : ''
    return 'api::' + raw + qs
  } catch {
    return 'api::' + raw
  }
}
