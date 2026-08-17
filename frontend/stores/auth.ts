import type { TokenResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

<<<<<<< Updated upstream
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const user = ref<any>(null)

  const isAuthenticated = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.is_staff || user.value?.is_superuser)

  function setTokens(tokens: TokenResponse) {
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    
    // Store in localStorage for persistence
    if (import.meta.client) {
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
    }
  }

=======
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

>>>>>>> Stashed changes
  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
<<<<<<< Updated upstream
    
=======

>>>>>>> Stashed changes
    if (import.meta.client) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }

  async function fetchUser() {
    if (!accessToken.value) return
<<<<<<< Updated upstream
    
    try {
      const { data } = await useFetch('/users/me', {
=======

    try {
      // useFetch 必须在 setup 上下文中调用；store 方法可能由事件回调触发，
      // 因此这里使用 $fetch（无上下文要求）并显式携带 baseURL
      user.value = await $fetch<AuthUser>('/users/me', {
        baseURL: apiBase,
>>>>>>> Stashed changes
        headers: {
          Authorization: `Bearer ${accessToken.value}`
        }
      })
<<<<<<< Updated upstream
      
      if (data.value) {
        user.value = data.value
      }
    } catch (error) {
      console.error('Failed to fetch user:', error)
      clearTokens()
=======
    } catch (error) {
      const status = (error as { status?: number })?.status
      if (status === 401) {
        clearTokens()
      } else {
        console.error('Failed to fetch user:', error)
      }
>>>>>>> Stashed changes
    }
  }

  async function login(username: string, password: string) {
    const { data, error } = await useAPI<TokenResponse>('/users/login', {
      method: 'POST',
      body: { username, password }
    })

    if (error.value) {
<<<<<<< Updated upstream
      const msg = (error.value.data as Record<string, any>)?.detail
      throw new Error(msg || 'Login failed')
=======
      const detail = (error.value.data as Record<string, unknown> | undefined)?.detail
      throw new Error(typeof detail === 'string' ? detail : 'Login failed')
>>>>>>> Stashed changes
    }

    if (data.value) {
      setTokens(data.value)
      await fetchUser()
    }
  }

  async function register(username: string, email: string, password: string, nickname?: string) {
    const { data, error } = await useAPI<TokenResponse>('/users/register', {
      method: 'POST',
      body: { username, email, password, nickname }
    })

    if (error.value) {
<<<<<<< Updated upstream
      const msg = (error.value.data as Record<string, any>)?.detail
      throw new Error(msg || 'Registration failed')
=======
      const detail = (error.value.data as Record<string, unknown> | undefined)?.detail
      throw new Error(typeof detail === 'string' ? detail : 'Registration failed')
>>>>>>> Stashed changes
    }

    if (data.value) {
      setTokens(data.value)
      await fetchUser()
    }
  }

  async function logout() {
    try {
      await useAPI('/users/logout', {
        method: 'POST',
        query: { refresh_token: refreshToken.value }
      })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearTokens()
    }
  }

<<<<<<< Updated upstream
  async function refreshAccessToken() {
    if (!refreshToken.value) {
      clearTokens()
      return false
    }

    try {
      const { data, error } = await useAPI<TokenResponse>('/users/refresh', {
        method: 'POST',
        body: { refresh_token: refreshToken.value }
      })

      if (error.value || !data.value) {
        clearTokens()
        return false
      }

      setTokens(data.value)
      return true
    } catch (error) {
      clearTokens()
      return false
    }
  }

  // Initialize from localStorage on client
  function initialize() {
    if (import.meta.client) {
      const storedAccessToken = localStorage.getItem('access_token')
      const storedRefreshToken = localStorage.getItem('refresh_token')
      
      if (storedAccessToken && storedRefreshToken) {
        accessToken.value = storedAccessToken
        refreshToken.value = storedRefreshToken
        fetchUser()
      }
    }
  }

=======
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
      const { error } = await useAPI('/me/avatar', {
        method: 'PUT',
        body: { avatar: url }
      })
      if (error.value) {
        // rollback if API disagrees
        if (prev && user.value && typeof user.value === 'object') {
          user.value = { ...user.value, avatar: prev }
        }
      }
    } catch (err) {
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

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
    updateAvatar,
>>>>>>> Stashed changes
    refreshAccessToken,
    initialize
  }
})
