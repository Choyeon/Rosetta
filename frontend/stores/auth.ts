import type { TokenResponse } from '~~/types/api'

export interface AuthUser {
  id: number
  username: string
  email?: string
  role?: string
  avatar?: string
  [k: string]: unknown
}

export const useAuthStore = defineStore('auth', () => {
  // store 首次实例化必然发生在组件 setup / middleware 中，此时 Nuxt 上下文可用
  const apiBase = useRuntimeConfig().public.apiBase as string

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
        baseURL: apiBase,
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
        baseURL: apiBase,
        method: 'POST',
        body: { username, password }
      })
      setTokens(data)
      await fetchUser()
    } catch (err) {
      const detail = (err as { data?: Record<string, unknown> })?.data?.detail
      throw new Error(typeof detail === 'string' ? detail : 'Login failed')
    }
  }

  async function register(username: string, email: string, password: string, nickname?: string) {
    try {
      const data = await $fetch<TokenResponse>('/users/register', {
        baseURL: apiBase,
        method: 'POST',
        body: { username, email, password, nickname }
      })
      setTokens(data)
      await fetchUser()
    } catch (err) {
      const detail = (err as { data?: Record<string, unknown> })?.data?.detail
      throw new Error(typeof detail === 'string' ? detail : 'Registration failed')
    }
  }

  async function logout() {
    try {
      await $fetch('/users/logout', {
        baseURL: apiBase,
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
   * Replace user's avatar URL locally and notify backend via PUT /me/avatar.
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
      await $fetch('/me/avatar', {
        baseURL: apiBase,
        method: 'PUT',
        body: { avatar: url },
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

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) {
      clearTokens()
      return false
    }

    try {
      // 与 fetchUser 同理：使用 $fetch，避免 useFetch 的上下文限制
      const data = await $fetch<TokenResponse>('/users/refresh', {
        baseURL: apiBase,
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
    }
  }

  let initialized = false
  let initPromise: Promise<void> | null = null

  // Initialize from localStorage on client; idempotent & concurrency-safe
  function initialize(): Promise<void> {
    if (!import.meta.client) return Promise.resolve()
    if (initialized) return Promise.resolve()
    if (initPromise) return initPromise

    initPromise = (async () => {
      try {
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
      }
    })()
    return initPromise
  }

  return {
    accessToken,
    refreshToken,
    user,
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
