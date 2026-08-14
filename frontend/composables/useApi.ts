import { useAuthStore } from '~~/stores/auth'

export const useAPI = <T = any>(url: string, options?: any) => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const defaultOptions = {
    baseURL: config.public.apiBase,
    headers: {} as Record<string, string>,
    server: false, // 纯 SPA：禁止在服务端执行 useFetch，避免 SSR 相关 payload / 序列化崩溃
    ...options
  }

  // Add auth token if available
  if (authStore.accessToken) {
    defaultOptions.headers.Authorization = `Bearer ${authStore.accessToken}`
  }

  // Add language header
  const { locale } = useI18n()
  defaultOptions.headers['Accept-Language'] = locale.value

  return useFetch<T>(url, {
    ...defaultOptions,
    async onResponseError({ response }) {
      // Handle 401 errors by attempting to refresh token
      if (response.status === 401 && authStore.refreshToken) {
        const refreshed = await authStore.refreshAccessToken()
        if (refreshed) {
          // Retry the request with new token
          return useFetch<T>(url, {
            ...defaultOptions,
            headers: {
              ...defaultOptions.headers,
              Authorization: `Bearer ${authStore.accessToken}`
            }
          })
        } else {
          // Refresh failed, redirect to login
          navigateTo('/login')
        }
      }
    }
  })
}

export const useAPILazy = <T = any>(url: string, options?: any) => {
  return useAPI<T>(url, { ...options, lazy: true })
}
