/**
 * 认证 store：token / user 的唯一前端真源，真值持久化在 localStorage。
 * SSR 侧永远渲染为未登录（三态均 skipHydrate）；initialize() 必须等 hydrate 完成
 * （app:mounted）后才回填，纯 CSR 空壳页（serverRendered=false）则要立即恢复，否则
 * 等 hook 的 router middleware 会死锁。刷新互斥 _refreshInFlight 保护后端 rotate 语义的
 * refresh_token（并发刷新第 2..N 个会吃到 TOKEN_REUSED 被踢下线）；store 内请求一律 $fetch
 * 并按端推导 baseURL（事件回调里调 useFetch 会静默不执行）。
 */
import type { TokenResponse } from '~~/types/api'
// Pinia skipHydrate：标记某些 state 为「不需要参与 SSR → 客户端的 payload 序列化/反序列化」
// 因为 token/user 的 source of truth 永远是 localStorage，
// SSR 阶段它们都是 null，序列化不但没有意义，还会因为 @pinia/nuxt payload-plugin
// 在极端情况下（值为 null + devalue stringify 遍历 Object.create(null) 形对象）
// 抛出 "obj.hasOwnProperty is not a function"，导致整个 payload 序列化崩溃、
// 所有页面的 useFetch 数据都进不了 payload（表现为"列表页空、首页碰巧能显示"）。
import { skipHydrate } from 'pinia'

export interface AuthUser {
  id: number
  username: string
  email?: string
  role?: string
  avatar?: string
  [k: string]: unknown
}

/**
 * 从后端失败响应里解析人类可读文案，优先级 message > detail > errors[0].message > 兜底。
 * 后端统一失败信封（AGENTS.md §7.2）只在 422 校验等 FastAPI 原生异常时带 detail，
 * 业务失败带的是 message / error_code / errors；只看 detail 会把真实错误吞成兜底文案。
 */
function extractApiMessage(data: Record<string, unknown>, fallback: string): string {
  const message = typeof data.message === 'string' ? data.message : ''
  const detail = typeof data.detail === 'string' ? data.detail : ''
  const errors = Array.isArray(data.errors) ? data.errors : []
  const firstFieldMsg
    = errors.length > 0 && errors[0] && typeof errors[0] === 'object' && typeof (errors[0] as { message?: string }).message === 'string'
      ? (errors[0] as { message: string }).message
      : ''
  return message || detail || firstFieldMsg || fallback
}

/**
 * login() 抛出的结构化错误：在普通 Error 之外携带后端错误码与剩余锁定秒数，
 * 让登录页能区分"密码错"与"账号被锁"并对后者展示倒计时（而非笼统报错）。
 * retryAfterSeconds 仅在 ACCOUNT_LOCKED / HTTP 423 时 > 0。
 */
export interface AuthLoginError extends Error {
  errorCode?: string
  status?: number
  retryAfterSeconds?: number
}

export const useAuthStore = defineStore('auth', () => {
  // store 首次实例化必然发生在组件 setup / middleware 中，此时 Nuxt 上下文可用。
  // ⚠️ SSR 关键：不能只读 public.apiBase（客户端相对路径 /api），
  // 服务器端必须直连 runtimeConfig.apiBase（绝对地址 http://host:port/api），
  // 否则 Nitro 会把 /users/login 作为「Nitro 内部 server route」匹配，命中 404，
  // 导致 SSR 刷新登录态 / SSR 下执行 refreshToken 静默失败。
  const _runtime = useRuntimeConfig()
  function getApiBase(): string {
    const priv = _runtime as unknown as { apiBase?: string }
    const pub = _runtime.public as unknown as { apiBase?: string }
    return (import.meta.server ? (priv.apiBase || '') : (pub.apiBase || '')) as string
  }

  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const user = ref<AuthUser | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)
  // 后端（backend/core/auth.py）以 is_staff / is_superuser 判定管理权限，
  // 同时兼容 role 字符串（admin / staff / superuser / 超级管理员）
  const isAdmin = computed(() => {
    const u = user.value
    if (!u) return false
    if (u.is_staff === true || u.is_superuser === true) return true
    const role = typeof u.role === 'string' ? u.role.toLowerCase() : ''
    return ['admin', 'staff', 'superuser', 'superadmin', '超级管理员'].includes(role)
  })

  function setTokens(tokens: TokenResponse) {
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token

    // Store in localStorage for persistence
    if (import.meta.client) {
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
    }
  }

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null

    if (import.meta.client) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }

  async function fetchUser() {
    if (!accessToken.value) return

    try {
      // useFetch 必须在 setup 上下文中调用；store 方法可能由事件回调触发，
      // 因此这里使用 $fetch（无上下文要求）并显式携带 baseURL
      user.value = await $fetch<AuthUser>('/users/me', {
        baseURL: getApiBase(),
        headers: {
          Authorization: `Bearer ${accessToken.value}`
        }
      })
    } catch (error) {
      const status = (error as { status?: number })?.status
      if (status === 401) {
        clearTokens()
      } else {
        console.error('Failed to fetch user:', error)
      }
    }
  }

  async function login(username: string, password: string) {
    // 与 fetchUser 同理：login 总在事件回调（按钮点击）中触发，
    // useFetch/useAPI 要求 setup 上下文，脱离上下文会静默不执行 —— 必须用 $fetch
    try {
      const data = await $fetch<TokenResponse>('/users/login', {
        baseURL: getApiBase(),
        method: 'POST',
        body: { username, password }
      })
      setTokens(data)
      await fetchUser()
    } catch (err) {
      // 后端统一响应结构：{ success:false, message, error_code?, errors?, retry_after_seconds? }
      // 某些 FastAPI 未捕获异常（如 422 校验）会带 { detail }，两者都取
      const data = (err as { data?: Record<string, unknown> })?.data ?? {}
      const status = (err as { status?: number, statusCode?: number })?.status
        ?? (err as { statusCode?: number })?.statusCode
      const errorCode = typeof data.error_code === 'string' ? data.error_code : ''
      const msg = extractApiMessage(data, '登录失败，请稍后再试')
      // 423 ACCOUNT_LOCKED：把剩余锁定秒数随错误一起外泄，登录页据此展示倒计时
      // （契约见 backend/docs/error_codes.md 限流段——不能只丢一句笼统报错）。
      const rawRetry = data.retry_after_seconds
      const retryAfterSeconds = typeof rawRetry === 'number' && rawRetry > 0 ? Math.ceil(rawRetry) : 0
      const loginError = new Error(msg) as AuthLoginError
      loginError.cause = err
      loginError.errorCode = errorCode
      loginError.status = typeof status === 'number' ? status : undefined
      loginError.retryAfterSeconds = errorCode === 'ACCOUNT_LOCKED' || status === 423 ? retryAfterSeconds : 0
      throw loginError
    }
  }

  async function register(username: string, email: string, password: string, nickname?: string) {
    try {
      const data = await $fetch<TokenResponse>('/users/register', {
        baseURL: getApiBase(),
        method: 'POST',
        body: { username, email, password, nickname }
      })
      setTokens(data)
      await fetchUser()
    } catch (err) {
      const data = (err as { data?: Record<string, unknown> })?.data ?? {}
      // 与 login 同源：读统一失败信封的 message / errors，别把 WEAK_PASSWORD、
      // EMAIL_EXISTS 这类真实业务错误吞成兜底文案。
      const regError = new Error(extractApiMessage(data, 'Registration failed')) as AuthLoginError
      regError.cause = err
      regError.errorCode = typeof data.error_code === 'string' ? data.error_code : ''
      throw regError
    }
  }

  async function logout() {
    try {
      await $fetch('/users/logout', {
        baseURL: getApiBase(),
        method: 'POST',
        query: { refresh_token: refreshToken.value }
      })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearTokens()
    }
  }

  /**
   * Replace user's avatar URL locally and notify backend via PUT /users/me/avatar.
   * Backend reads the avatar from the `avatar` query parameter (see backend/api/users.py).
   * Backend call is best-effort: even when offline the UI reflects the new avatar
   * so user can see crop + upload result visually immediately.
   */
  async function updateAvatar(url: string) {
    if (!url) return
    const prev = user.value?.avatar ?? null
    if (user.value && typeof user.value === 'object') {
      user.value = { ...user.value, avatar: url }
    }
    try {
      await $fetch('/users/me/avatar', {
        baseURL: getApiBase(),
        method: 'PUT',
        query: { avatar: url },
        headers: accessToken.value ? { Authorization: `Bearer ${accessToken.value}` } : {}
      })
    } catch (err) {
      // rollback if API disagrees
      if (prev && user.value && typeof user.value === 'object') {
        user.value = { ...user.value, avatar: prev }
      }
      console.warn('[auth.updateAvatar] backend unreachable, kept UI-only avatar:', err)
    }
  }

  // 并发 401 刷新互斥：多个请求同时拿过期 access token 撞 401 时，
  // 只允许一个真正的 /users/refresh 请求（后端是 rotate 语义，刷新令牌单次有效；
  // 并发刷新会让第 2..N 个请求吃到 TOKEN_REUSED，把刚刷新成功的用户踢下线）。
  let _refreshInFlight: Promise<boolean> | null = null

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) {
      clearTokens()
      return false
    }
    if (_refreshInFlight) return _refreshInFlight

    _refreshInFlight = (async () => {
      try {
        // 与 fetchUser 同理：使用 $fetch，避免 useFetch 的上下文限制
        const data = await $fetch<TokenResponse>('/users/refresh', {
          baseURL: getApiBase(),
          method: 'POST',
          body: { refresh_token: refreshToken.value }
        })

        if (!data?.access_token) {
          clearTokens()
          return false
        }

        setTokens(data)
        return true
      } catch {
        clearTokens()
        return false
      } finally {
        _refreshInFlight = null
      }
    })()
    return _refreshInFlight
  }

  let initialized = false
  let initPromise: Promise<void> | null = null

  /**
   * 从 localStorage 恢复登录态。
   *
   * ⚠️ Hydration 安全：
   *  SSR 永远渲染为「未登录」（没有 localStorage / cookie 存 JWT）。
   *  如果客户端首屏在 hydrate 完成前同步读取 localStorage 并赋值 accessToken / user，
   *  会让 Header 从「登录按钮」变「用户头像」，触发大面积 Hydration mismatch
   *  （Vue 报错 "Hydration completed but contains mismatches."）。
   *
   *  因此 SSR 页面必须等 app:mounted（hydrate 完成）后再恢复 token。
   *  两点关键约束：
   *   1. app:mounted 是唯一放行点——超时只告警不抢跑。低端机首帧超阈值时抢跑
   *      写入正是这里要防的 mismatch；挂载只是慢不是死，hook 最终仍会触发。
   *   2. ssr:false 空壳页（/admin /login /register）没有可 mismatch 的服务端
   *      HTML，且它们的 middleware/page-setup 会 await 本函数——router.isReady
   *      阻塞挂载、挂载才触发 app:mounted，等待该 hook 会直接死锁，
   *      所以 serverRendered=false 时必须立即恢复。
   */
  function initialize(): Promise<void> {
    if (!import.meta.client) return Promise.resolve()
    if (initialized) return Promise.resolve()
    if (initPromise) return initPromise

    const nuxtApp = useNuxtApp()
    // 判断是否仍处于「有真实 HTML 待 hydrate 且尚未完成」的首屏阶段：
    //   · payload.serverRendered=false → 纯 CSR 首渲染，写状态就是首帧本身，无 mismatch
    //   · document.readyState === 'loading' → 还在解析 HTML，必是首屏 hydrating
    //   · window.__NUXT_HYDRATED__ 未打标 → 仍在 hydrate 过程中
    const serverRendered = !!nuxtApp.payload?.serverRendered
    const isHydrating = serverRendered
      && ((typeof document !== 'undefined' && document.readyState === 'loading')
        || !(typeof window !== 'undefined' && (window as { __NUXT_HYDRATED__?: boolean }).__NUXT_HYDRATED__))

    initPromise = (async () => {
      try {
        // 首屏阶段 → 等 Vue/Nuxt 挂载完成（hydrate 结束）再改状态，避免 mismatch
        if (isHydrating) {
          await new Promise<void>((resolve) => {
            // app:mounted = Vue app 实例已挂载（hydrate 完成）；这是唯一放行点。
            let released = false
            nuxtApp.hook('app:mounted', () => {
              released = true
              resolve()
            })
            // 仅观测用途：慢挂载时提示，但绝不提前写状态（那等于恢复旧超时抢跑 bug）。
            setTimeout(() => {
              if (!released) {
                console.warn('[auth] app:mounted >8s 未触发，登录态恢复继续等待挂载完成')
              }
            }, 8000)
          })
        }

        const storedAccessToken = localStorage.getItem('access_token')
        const storedRefreshToken = localStorage.getItem('refresh_token')

        if (storedAccessToken && storedRefreshToken) {
          accessToken.value = storedAccessToken
          refreshToken.value = storedRefreshToken
          await fetchUser()
        }
      } finally {
        initialized = true
        initPromise = null
        if (import.meta.client && typeof window !== 'undefined') {
          ;(window as { __NUXT_HYDRATED__?: boolean }).__NUXT_HYDRATED__ = true
        }
      }
    })()
    return initPromise
  }

  return {
    // 认证相关状态：从 localStorage 恢复，不参与 SSR payload hydrate
    accessToken: skipHydrate(accessToken),
    refreshToken: skipHydrate(refreshToken),
    user: skipHydrate(user),
    isAuthenticated,
    isAdmin,
    setTokens,
    clearTokens,
    fetchUser,
    login,
    register,
    logout,
    updateAvatar,
    refreshAccessToken,
    initialize
  }
})
