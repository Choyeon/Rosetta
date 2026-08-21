/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { useAuthStore } from '~~/stores/auth'
import {
  extractApiErrorMessage,
  isOobeRequiredError,
  stableApiKey,
  type ApiErrorBody,
  type ApiFetchOptions
} from '~~/lib/utils'

/** 后端统一错误响应体 & 请求项结构：纯声明在 lib/utils.ts，组件侧复用即可。 */
export type { ApiFetchOptions }
export type { ApiErrorBody }

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

export function useAPI<T>(url: string | (() => string), options?: UseFetchOptions<T>) {
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

  // 关键：SSR 环境下，Nitro 内部路由与 devProxy 是两套机制，
  // 若用 config.public.apiBase（值为 '/api' 相对路径），会走 Nitro 自身
  // 内部路由匹配命中 404，导致前端页面 SSR 渲染为加载错误态。
  // 因此服务端用 config.apiBase（绝对地址直连后端），客户端继续用
  // 相对地址 /api，经浏览器请求走 devProxy 反向代理到 FastAPI。
  const ssrSafeBase = import.meta.server ? config.apiBase : config.public.apiBase
  // 如果调用方未传自定义 key，则生成稳定 key；若已传则以调用方为准。
  const stableKey = options?.key ?? stableApiKey(url, options?.query as Record<string, unknown> | undefined)
  return useFetch<T>(url, {
    // 默认在 SSR 时执行（配合全局 ssr:true + 公开页面），
    // 调用方可通过 options.server: false 显式关闭（如管理后台需要登录态、只在客户端拉的场景）。
    // 这是修复"从文章详情返回列表/首页页面空白"的关键一环：
    // 旧版强制 server:false + onMounted 调用 useFetch 导致：
    //   1) SSR 不执行，首屏 HTML 无数据（搜索引擎爬不到，解决 SEO 空白）；
    //   2) 客户端组件复用时 onMounted 不再触发 + useFetch 丢失上下文，
    //      返回的 AsyncData 仍为空，出现"路由跳转后页面空白、刷新才恢复"。
    ...options,
    key: stableKey,
    baseURL: ssrSafeBase,
    headers,
    async onResponseError({ response }) {
      const body = response._data as unknown
      // 注意：SSR 服务器端的 onResponseError 绝不能调用 navigateTo（客户端路由 API），
      // 否则会在 Nitro 渲染线程中抛异常或让 Promise 永远 pending，
      // 导致 useFetch 卡住、结果永远 pending=true、客户端 hydration 后不重试，页面永久空白。
      if (import.meta.client) {
        if (isOobeRequiredError(response.status, body)) {
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

  // SSR-safe：服务端直连 FastAPI 绝对地址（不走 Nitro 内部路由匹配 404）
  const baseURL = import.meta.server ? config.apiBase : config.public.apiBase

  const doFetch = () => $fetch<T>(url, {
    ...options,
    baseURL,
    headers: buildHeaders()
  })

  try {
    return await doFetch()
  } catch (err) {
    const e = err as { status?: number, statusCode?: number, data?: unknown }
    const status = e.status ?? e.statusCode ?? 0

    if (isOobeRequiredError(status, e.data)) {
      await navigateTo('/oobe')
      throw err
    }

    if (status === 404) {
      // 404 在前端开发阶段很常见：后端路由还没补齐 / 拼写错误；不要打断用户工作流，
      // 只在控制台打印具体 URL 方便定位，然后抛错（让调用方自己决定是否降级）。

      console.warn('[useAPI] 404 Not Found', {
        method: options.method || 'GET',
        url,
        data: e.data
      })
      const msg = extractApiErrorMessage(e.data, `Not Found: ${url}`)
      throw Object.assign(new Error(msg), { status, data: e.data, code: 'NOT_FOUND' })
    }

    if (status === 401) {
      const refreshed = await authStore.refreshAccessToken()
      if (refreshed) {
        try {
          return await doFetch()
        } catch (retryErr) {
          const re = retryErr as { status?: number, statusCode?: number, data?: unknown }
          const retryStatus = re.status ?? re.statusCode ?? 0
          if (isOobeRequiredError(retryStatus, re.data)) {
            await navigateTo('/oobe')
            throw retryErr
          }
          if (retryStatus === 401) {
            authStore.clearTokens()
            await navigateTo('/login')
            throw retryErr
          }
          safeToastError(extractApiErrorMessage(re.data, '请求失败'))
          throw retryErr
        }
      }
      authStore.clearTokens()
      await navigateTo('/login')
      throw err
    }

    safeToastError(extractApiErrorMessage(e.data, '请求失败'))
    throw err
  }
}

/**
 * 静默版 apiFetch：出错不 toast（由调用方自行降级），仅用于"可缺失"的辅助功能，
 * 例如站内通知 badge，后端暂未实现或升级中时保持 UI 稳定不报错。
 */
export async function silentApiFetch<T = unknown>(url: string, options: ApiFetchOptions = {}): Promise<T | null> {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const buildHeaders = (): Record<string, string> => {
    const h: Record<string, string> = { ...options.headers, 'Accept-Language': currentLocale() }
    if (authStore.accessToken) {
      h.Authorization = `Bearer ${authStore.accessToken}`
    }
    return h
  }

  // SSR-safe：服务端直连 FastAPI 绝对地址（不走 Nitro 内部路由匹配 404）
  const baseURL = import.meta.server ? config.apiBase : config.public.apiBase

  const doFetch = () => $fetch<T>(url, {
    ...options,
    baseURL,
    headers: buildHeaders()
  })

  try {
    return await doFetch()
  } catch (err) {
    const e = err as { status?: number, statusCode?: number, data?: unknown }
    const status = e.status ?? e.statusCode ?? 0

    if (isOobeRequired(status, e.data) && import.meta.client) {
      await navigateTo('/oobe')
      return null
    }

    if (status === 401) {
      if (import.meta.client) {
        const refreshed = await authStore.refreshAccessToken()
        if (refreshed) {
          try {
            return await doFetch()
          } catch {
            /* swallow */
            return null
          }
        }
        authStore.clearTokens()
        await navigateTo('/login')
      } else {
        authStore.clearTokens()
      }
      return null
    }

    // 其余错误：静默降级，避免 console 外还要 toast

    console.debug(`[silentApiFetch] ${options.method || 'GET'} ${url} -> ${status}`, extractApiErrorMessage(e.data, 'silent failure'))
    return null
  }
}
