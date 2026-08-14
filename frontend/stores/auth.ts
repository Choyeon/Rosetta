import type { TokenResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

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
      const { data } = await useFetch('/users/me', {
        headers: {
          Authorization: `Bearer ${accessToken.value}`
        }
      })
      
      if (data.value) {
        user.value = data.value
      }
    } catch (error) {
      console.error('Failed to fetch user:', error)
      clearTokens()
    }
  }

  async function login(username: string, password: string) {
    const { data, error } = await useAPI<TokenResponse>('/users/login', {
      method: 'POST',
      body: { username, password }
    })

    if (error.value) {
      const msg = (error.value.data as Record<string, any>)?.detail
      throw new Error(msg || 'Login failed')
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
      const msg = (error.value.data as Record<string, any>)?.detail
      throw new Error(msg || 'Registration failed')
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
    refreshAccessToken,
    initialize
  }
})
