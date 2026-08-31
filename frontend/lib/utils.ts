import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
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

/**
 * hex → HSL 空格三元组字符串（如 "181 84% 36%"）。
 * 直接喂给 hsl(...) 语法 / color-mix 计算。
 */
export function hexToHslTriple(hex: string): string | null {
  const hsl = hexToHsl(hex)
  if (!hsl) return null
  return `${hsl.h} ${hsl.s}% ${hsl.l}%`
}

/**
 * 根据 WCAG 相对亮度公式计算亮度 (0~1)。
 * 用于自动选择前景色：>0.6 → 深色文字，否则白色。
 */
export function hexRelativeLuminance(hex: string): number {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(String(hex).trim())
  if (!m) return 0.5
  const toLin = (v: number) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
  const r = toLin(parseInt(m[1] ?? '00', 16) / 255)
  const g = toLin(parseInt(m[2] ?? '00', 16) / 255)
  const b = toLin(parseInt(m[3] ?? '00', 16) / 255)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

// ====================== API 纯工具（供 useApi.ts 与单元测试共享） ======================

/** Rosetta 后端统一错误响应体，纯字段声明。 */
export interface ApiErrorBody {
  message?: string
  error_code?: string
  errors?: Array<{ field?: string, message?: string }>
  detail?: unknown
  [k: string]: unknown
}

/**
 * 从错误响应体提取用户可读信息，纯函数、零依赖组件上下文，直接可测。
 *
 * 优先级：message → detail → errors[0].message → fallback。
 */
export function extractApiErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const b = body as ApiErrorBody
    if (typeof b.message === 'string' && b.message) return b.message
    if (typeof b.detail === 'string' && b.detail) return b.detail
    if (Array.isArray(b.errors) && b.errors.length) {
      const first = b.errors[0]
      if (first && typeof first.message === 'string' && first.message) return first.message
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
