/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { useAuthStore } from '~~/stores/auth'

/** 后端统一错误响应体（{ success, message, error_code, errors } 或 FastAPI 的 detail） */
interface ApiErrorBody {
  message?: string
  error_code?: string
  errors?: Array<{ field?: string, message?: string }>
  detail?: unknown
  [k: string]: unknown
}

/** apiFetch 的请求选项（透传给 $fetch） */
export interface ApiFetchOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD'
  body?: unknown
  query?: Record<string, unknown>
  headers?: Record<string, string>
  [k: string]: unknown
}

/** 从错误响应体中提取用户可读信息 */
function extractErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const b = body as ApiErrorBody
    if (typeof b.message === 'string' && b.message) return b.message
    if (typeof b.detail === 'string' && b.detail) return b.detail
    if (Array.isArray(b.errors) && b.errors.length) {
      const first = b.errors[0]
      if (first && typeof first.message === 'string') return first.message
    }
  }
  return fallback
}

/** 后端 OOBE 未完成：503 + error_code: OOBE_REQUIRED */
function isOobeRequired(status: number, body: unknown): boolean {
  return status === 503 && (body as ApiErrorBody | null | undefined)?.error_code === 'OOBE_REQUIRED'
}

/** useToast / useI18n 依赖组件上下文；脱离上下文（事件回调链）时降级，不中断流程 */
function safeToastError(message: string) {
  try {
    useToast().error(message)
  } catch {
    console.error('[useAPI]', message)
  }
}

function currentLocale(): string {
  try {
    return useI18n().locale.value
  } catch {
    return 'zh'
  }
}

/**
 * useFetch 封装：自动注入 baseURL / Authorization / Accept-Language。
 *
 * 限制：useFetch 的错误钩子内无法重试当前请求（递归 useFetch 不会让调用方拿到新结果），
 * 401 时仅尝试刷新 token 供后续请求使用；需要"刷新后自动重试"请使用 apiFetch。
 */
export function useAPI<T>(url: string, options?: UseFetchOptions<T>) {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()
  const { locale } = useI18n()

  const headers: Record<string, string> = { 'Accept-Language': locale.value }
  if (options?.headers && typeof options.headers === 'object' && !Array.isArray(options.headers)) {
    Object.assign(headers, options.headers as Record<string, string>)
  }
  if (authStore.accessToken) {
    headers.Authorization = `Bearer ${authStore.accessToken}`
  }

  return useFetch<T>(url, {
    // 默认在 SSR 时执行（配合全局 ssr:true + 公开页面），
    // 调用方可通过 options.server: false 显式关闭（如管理后台需要登录态、只在客户端拉的场景）。
    // 这是修复"从文章详情返回列表/首页页面空白"的关键一环：
    // 旧版强制 server:false + onMounted 调用 useFetch 导致：
    //   1) SSR 不执行，首屏 HTML 无数据（搜索引擎爬不到，解决 SEO 空白）；
    //   2) 客户端组件复用时 onMounted 不再触发 + useFetch 丢失上下文，
    //      返回的 AsyncData 仍为空，出现"路由跳转后页面空白、刷新才恢复"。
    ...options,
    baseURL: config.public.apiBase,
    headers,
    async onResponseError({ response }) {
      const body = response._data as unknown
      // 注意：SSR 服务器端的 onResponseError 绝不能调用 navigateTo（客户端路由 API），
      // 否则会在 Nitro 渲染线程中抛异常或让 Promise 永远 pending，
      // 导致 useFetch 卡住、结果永远 pending=true、客户端 hydration 后不重试，页面永久空白。
      if (import.meta.client) {
        if (isOobeRequired(response.status, body)) {
          await navigateTo('/oobe')
          return
        }
        if (response.status === 401 && authStore.refreshToken) {
          const refreshed = await authStore.refreshAccessToken()
          if (!refreshed) {
            authStore.clearTokens()
            await navigateTo('/login')
          }
        } else if (response.status === 401) {
          authStore.clearTokens()
          await navigateTo('/login')
        }
      } else {
        // SSR 端：401 / 503 只清理内部状态，不尝试路由跳转（跳转没有意义）
        if (response.status === 401) {
          authStore.clearTokens()
        }
      }
    }
  })
}

export function useAPILazy<T>(url: string, options?: UseFetchOptions<T>) {
  return useAPI<T>(url, { ...options, lazy: true })
}

/**
 * 基于 $fetch 的请求函数（无 setup 上下文要求，可在任意时机调用）：
 * - 自动携带 Authorization 与 Accept-Language
 * - 401 时用 refresh_token 刷新并自动重试一次；仍失败则清空登录态并跳转 /login
 * - 503 + OOBE_REQUIRED 时跳转 /oobe
 * - 其他错误统一 toast 提示后重新抛出
 */
export async function apiFetch<T = unknown>(url: string, options: ApiFetchOptions = {}): Promise<T> {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const buildHeaders = (): Record<string, string> => {
    const h: Record<string, string> = { ...options.headers, 'Accept-Language': currentLocale() }
    if (authStore.accessToken) {
      h.Authorization = `Bearer ${authStore.accessToken}`
    }
    return h
  }

  const doFetch = () => $fetch<T>(url, {
    ...options,
    baseURL: config.public.apiBase,
    headers: buildHeaders()
  })

  try {
    return await doFetch()
  } catch (err) {
    const e = err as { status?: number, statusCode?: number, data?: unknown }
    const status = e.status ?? e.statusCode ?? 0

    if (isOobeRequired(status, e.data)) {
      await navigateTo('/oobe')
      throw err
    }

    if (status === 401) {
      const refreshed = await authStore.refreshAccessToken()
      if (refreshed) {
        try {
          return await doFetch()
        } catch (retryErr) {
          const re = retryErr as { status?: number, statusCode?: number, data?: unknown }
          const retryStatus = re.status ?? re.statusCode ?? 0
          if (isOobeRequired(retryStatus, re.data)) {
            await navigateTo('/oobe')
            throw retryErr
          }
          if (retryStatus === 401) {
            authStore.clearTokens()
            await navigateTo('/login')
            throw retryErr
          }
          safeToastError(extractErrorMessage(re.data, '请求失败'))
          throw retryErr
        }
      }
      authStore.clearTokens()
      await navigateTo('/login')
      throw err
    }

    safeToastError(extractErrorMessage(e.data, '请求失败'))
    throw err
  }
}
