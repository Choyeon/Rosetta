import { toast as sonnerToast } from 'vue-sonner'
import type { UseFetchOptions } from '#app'
import { useAuthStore } from '~~/stores/auth'
import {
  extractApiErrorMessage,
  isOobeRequiredError,
  stableApiKey,
  type ApiErrorBody
} from '~~/lib/utils'

/**
 * useAPI 的 options 类型。
 *
 * 直接使用 Nuxt 的 UseFetchOptions<T> 会触发 Nitro TypedInternalResponse 的
 * 路由条件类型匹配，导致 TS2321 栈溢出（尤其在 open generic T 下）。
 * 这里用 Omit 去掉 default 的严格约束，允许 default: T | (() => T) 的常规写法，
 * 内部调用 useFetch 时再断言回 Nuxt 期望的类型。
 */
export type ApiUseFetchOptions<T> = Omit<UseFetchOptions<T>, 'default'> & {
  default?: T | (() => T) | Ref<T> | null
}

/**
 * 统一请求选项。
 * `silentToast`：为 true 时，apiFetch 出错**不**自动弹 toast（由调用方自行处理），
 * 用于避免"apiFetch 自动弹 + 页面 catch 再弹"造成同一错误弹两条的问题。
 * 默认 false：apiFetch 作为唯一自动 toaster，保证错误只弹一次。
 */
export interface ApiFetchOptions {
  method?: string
  headers?: Record<string, string>
  body?: unknown
  query?: Record<string, unknown>
  baseURL?: string
  server?: boolean
  key?: string
  silentToast?: boolean
  [key: string]: unknown
}

/** 后端统一错误响应体类型（透传 lib/utils 的定义）。 */
export type { ApiErrorBody }

/**
 * vue-sonner 的全局 toast 函数不依赖 Vue setup 上下文，
 * 因此在事件回调 / Promise catch / 异步链中也能正常弹出提示。
 */
function safeToastError(message: string) {
  try {
    sonnerToast.error(message)
  } catch {
    // 极端降级：连 sonner 都不可用，至少保留控制台信息
    console.error('[useAPI]', message)
  }
}

/**
 * 尽量从 Nuxt i18n 上下文取当前语言（SSR/客户端初始一致，避免 hydrate mismatch）。
 *
 * ⚠️ 关键约束：
 *  1. SSR 环境下不允许读 localStorage / navigator，否则 SSR 永远得到 zh，
 *     客户端 setup 同步阶段得到 en/ja/zh_Hant，两端 useFetch key 与 query 对不上，
 *     导致整页 Hydration mismatch + 首屏重复请求。
 *  2. 客户端「在 Nuxt 上下文里」调用（setup/plugin/middleware/useFetch 同步阶段）
 *     也必须走 $i18n.locale，因为 @nuxtjs/i18n 通过 cookie 保证 SSR 与客户端初始
 *     locale 完全一致。此时绝对不能读 localStorage，否则两边计算的 useFetch key
 *     对不上，Nuxt 会报 Cache key mismatch。
 *  3. 仅当「不在 Nuxt 上下文」（事件回调、独立工具函数）且是客户端时，才允许
 *     退化到 localStorage / navigator。
 */
export function currentLocale(): string {
  // 1) 最优先：在 Nuxt 上下文内（setup / plugin / middleware / useFetch options 同步计算阶段）
  //    → 通过 Nuxt i18n 注入的 $i18n.locale 拿值，SSR / 客户端初始完全一致。
  try {
    const i18n = useNuxtApp().$i18n as { locale?: Ref<string> } | undefined
    if (i18n?.locale?.value) {
      return i18n.locale.value
    }
  } catch {
    /* not inside Nuxt setup context; fall through */
  }

  // 2) SSR 兜底：不可能走到 localStorage / navigator，直接返回 'zh'。
  const serverSide = typeof import.meta !== 'undefined' && !!(import.meta as ImportMeta).server
  if (serverSide) return 'zh'

  // 3) 不在 Nuxt 上下文且是客户端：事件回调 / 独立工具函数里才允许读本地。
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('locale')
      if (stored) return stored
    } catch {
      /* storage disabled */
    }
    const nav = navigator.language || (navigator as { userLanguage?: string }).userLanguage
    if (nav?.startsWith('en')) return 'en'
    if (nav?.startsWith('ja')) return 'ja'
    if (nav?.startsWith('zh-Hant') || nav?.startsWith('zh-TW') || nav?.startsWith('zh-HK')) return 'zh_Hant'
  }
  return 'zh'
}

/**
 * 守卫：服务端渲染时，若后端地址（runtimeConfig.apiBase）为空，
 * 绝不能让 $fetch 以相对路径发起请求——那会变成对 Nuxt 自身的请求，
 * 而引导插件在每个自请求上再次运行，形成嵌套自请求放大直至堆溢出（OOM）。
 * 这里快速抛出明确错误，由各调用方的兜底 catch 处理（保持默认值/错误页）。
 */
function guardServerBase(base: unknown): asserts base is string {
  if (import.meta.server && !String(base ?? '').trim()) {
    const err = new Error(
      'SSR backend base is not configured. Set NUXT_API_BASE (or SSR_API_BASE_URL at build).'
    ) as Error & { code: string }
    err.code = 'SSR_BACKEND_BASE_MISSING'
    throw err
  }
}

export function useAPI<T>(url: string | (() => string), options?: ApiUseFetchOptions<T>) {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()
  // 避免在 setup 之外/异步链中调用 useI18n() 触发
  // "Must be called at the top of a setup function"
  const locale = currentLocale()

  const headers: Record<string, string> = { 'Accept-Language': locale }
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
  const callerOnRequest = options?.onRequest as ((ctx: unknown) => void) | undefined
  // 用 unknown 中转断开 Nitro TypedInternalResponse 路由条件类型推断链，
  // 否则 open generic T + options.default 会让 useFetch 重载匹配失败（TS2769）。
  // 泛型 T 仍然保证返回的 data.value 类型为 T。
  return useFetch<T>(url, {
    ...(options as unknown as Record<string, unknown>),
    key: stableKey,
    baseURL: ssrSafeBase,
    headers,
    onRequest(ctx: unknown) {
      guardServerBase(ssrSafeBase)
      callerOnRequest?.(ctx)
    },
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

export function useAPILazy<T>(url: string, options?: ApiUseFetchOptions<T>) {
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
  // 服务端缺后端地址：快速失败，禁止自请求放大 OOM（ensureLoaded 等调用方会兜底）
  guardServerBase(baseURL)

  // 注意：不能用 $fetch<T>(url, ...) 的显式泛型写法——T 为开放泛型时
  // Nitro 的 TypedInternalResponse 路由匹配条件类型会栈溢出（TS2321），
  // 且 ApiFetchOptions.method: string 与 ofetch 的 HTTP 方法联合类型不兼容。
  // 将 $fetch 擦除为普通函数类型，彻底断开 Nitro 路由类型推断链。
  const _fetch = $fetch as unknown as (
    url: string,
    opts?: Record<string, unknown>
  ) => Promise<unknown>
  const doFetch = (): Promise<T> =>
    _fetch(url, {
      ...options,
      baseURL,
      headers: buildHeaders()
    }) as Promise<T>

  try {
    return await doFetch()
  } catch (err) {
    const e = err as { status?: number, statusCode?: number, data?: unknown, cause?: unknown, message?: string }
    const status = e.status ?? e.statusCode ?? 0

    // —— 网络层错误（status === 0）：ERR_CONNECTION_RESET / timeout / abort / DNS 失败等
    // 这些错误没有 HTTP response body，必须特殊处理以给出明确 toast
    if (status === 0) {
      const raw = (e.message || '') + ' ' + String(e.cause ?? '')
      let hint = '网络连接失败，请检查后端服务是否正常'
      if (/abort/i.test(raw)) hint = '请求已取消（上传超时），请重试或上传更小的文件'
      else if (/timeout|timed?\s*out/i.test(raw)) hint = '请求超时，请检查网络或稍后重试'
      else if (/connection\s*reset|ECONNRESET|network/i.test(raw)) hint = '连接被重置，后端可能正在重启或文件过大，请稍后重试'
      else if (/Failed to fetch/i.test(raw)) hint = '无法连接到后端服务，请确认已启动后端或检查网络'
      console.error('[useAPI] 网络层错误', { method: options.method || 'GET', url, err })
      if (!options.silentToast) safeToastError(hint)
      throw Object.assign(new Error(hint), { status: 0, code: 'NETWORK_ERROR', cause: err })
    }

    if (isOobeRequiredError(status, e.data)) {
      await navigateTo('/oobe')
      throw err
    }

    if (status === 404) {
      // 404：后端路由缺失 / 拼写错误 / 资源不存在，管理员执行 CRUD 时遇到就是操作失败，
      // 必须给出明确 toast，不能静默（否则用户以为"保存成功了"实际根本没写入）。
      console.warn('[useAPI] 404 Not Found', {
        method: options.method || 'GET',
        url,
        data: e.data
      })
      const msg = extractApiErrorMessage(e.data, `接口不存在 (404): ${url}`)
      if (!options.silentToast) safeToastError(msg)
      throw Object.assign(new Error(msg), { status, data: e.data, code: 'NOT_FOUND' })
    }

    if (status === 413) {
      const msg = extractApiErrorMessage(e.data, '文件过大，超过服务器允许的上传大小')
      if (!options.silentToast) safeToastError(msg)
      throw Object.assign(new Error(msg), { status, data: e.data, code: 'PAYLOAD_TOO_LARGE' })
    }

    if (status === 401) {
      const refreshed = await authStore.refreshAccessToken()
      if (refreshed) {
        try {
          return await doFetch()
        } catch (retryErr) {
          const re = retryErr as { status?: number, statusCode?: number, data?: unknown, cause?: unknown, message?: string }
          const retryStatus = re.status ?? re.statusCode ?? 0
          // 重试后若再次出现网络层错误，也要给 toast
          if (retryStatus === 0) {
            const hint = '重试时网络中断，请检查后端服务状态'
            console.error('[useAPI] 401 重试后网络错误', { url, retryErr })
            if (!options.silentToast) safeToastError(hint)
            throw Object.assign(new Error(hint), { status: 0, code: 'NETWORK_ERROR', cause: retryErr })
          }
          if (isOobeRequiredError(retryStatus, re.data)) {
            await navigateTo('/oobe')
            throw retryErr
          }
          if (retryStatus === 401) {
            authStore.clearTokens()
            await navigateTo('/login')
            throw retryErr
          }
          if (!options.silentToast) {
            safeToastError(extractApiErrorMessage(re.data, '请求失败'))
          }
          throw retryErr
        }
      }
      authStore.clearTokens()
      await navigateTo('/login')
      throw err
    }

    if (!options.silentToast) {
      safeToastError(extractApiErrorMessage(e.data, '请求失败'))
    }
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
  // 服务端缺后端地址：快速失败返回 null，禁止自请求放大 OOM
  guardServerBase(baseURL)

  // 同 apiFetch：将 $fetch 擦除为普通函数类型，避免 TS2321 类型栈溢出
  const _fetch = $fetch as unknown as (
    url: string,
    opts?: Record<string, unknown>
  ) => Promise<unknown>
  const doFetch = (): Promise<T> =>
    _fetch(url, {
      ...options,
      baseURL,
      headers: buildHeaders()
    }) as Promise<T>

  try {
    return await doFetch()
  } catch (err) {
    const e = err as { status?: number, statusCode?: number, data?: unknown }
    const status = e.status ?? e.statusCode ?? 0

    if (isOobeRequiredError(status, e.data) && import.meta.client) {
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
