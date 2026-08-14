import type { OOBEStatus, OOBEInstallRequest, TokenResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'
import { useAuthStore } from '~~/stores/auth'

export const useOOBE = () => {
  const status = ref<OOBEStatus | null>(null)
  const loading = ref(false)
  const error = ref<any>(null)
  const authStore = useAuthStore()

  const getOOBEStatus = async () => {
    const { data, error: err } = await useAPI<OOBEStatus>('/oobe/status')
    if (!err.value) status.value = data.value ?? null
    return { data, error: err }
  }

  const checkEnvironment = () => {
    return useAPI('/oobe/check')
  }

  const getSystemInfo = () => {
    return useAPI('/oobe/system-info')
  }

  const checkDependencies = () => {
    return useAPI('/oobe/dependencies')
  }

  const installDependencies = () => {
    return useAPI('/oobe/install-dependencies', {
      method: 'POST'
    })
  }

  const install = (data: OOBEInstallRequest) => {
    return useAPI('/oobe/install', {
      method: 'POST',
      body: data
    })
  }

  const getInstallStream = (sid: string) => {
    const config = useRuntimeConfig()
    return new EventSource(`${config.public.apiBase}/oobe/install/stream?sid=${sid}`)
  }

  // Friendly aliases used by the wizard UI
  const checkSystem = async () => {
    loading.value = true
    error.value = null
    try {
      const { data, error: err } = await checkEnvironment()
      if (err.value) throw err.value
      status.value = { ...(status.value || {} as any), systemChecks: data.value }
      return data.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  const createAdmin = async (payload: { username: string; email: string; password: string; nickname?: string }) => {
    loading.value = true
    error.value = null
    try {
      const { data: regData, error: regErr } = await useAPI<TokenResponse>('/users/register', {
        method: 'POST',
        body: {
          username: payload.username,
          password: payload.password,
          email: payload.email,
          nickname: payload.nickname
        }
      })
      if (regErr.value) throw regErr.value

      const { data: loginData, error: loginErr } = await useAPI<TokenResponse>('/users/login', {
        method: 'POST',
        body: {
          username: payload.username,
          password: payload.password
        }
      })
      if (loginErr.value) throw loginErr.value

      if (loginData.value) {
        authStore.setTokens(loginData.value)
        await authStore.fetchUser()
      }

      status.value = { ...(status.value || {} as any), adminCreated: true, adminUser: payload }
      return status.value
    } finally {
      loading.value = false
    }
  }

  const saveSiteSettings = async (settings: { siteName: string; description: string; defaultLocale: string; seoKeywords: string }) => {
    loading.value = true
    error.value = null
    try {
      status.value = { ...(status.value || {} as any), siteConfigured: true, siteSettings: settings }
      return status.value
    } finally {
      loading.value = false
    }
  }

  const finishOOBE = async () => {
    loading.value = true
    error.value = null
    try {
      const st = status.value || {} as any
      const adminUser = st.adminUser || {}
      const siteSettings = st.siteSettings || {}
      const payload: OOBEInstallRequest = {
        admin_username: adminUser.username,
        admin_email: adminUser.email,
        admin_password: adminUser.password,
        admin_nickname: adminUser.nickname,
        site_name: siteSettings.siteName,
        site_description: siteSettings.description,
        default_locale: siteSettings.defaultLocale,
        seo_keywords: siteSettings.seoKeywords
      } as any
      const { data, error: err } = await install(payload)
      if (err.value) throw err.value
      status.value = { ...(status.value || {} as any), initialized: true }
      return data.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    // state
    status,
    loading,
    error,
    // raw AsyncData API
    getOOBEStatus,
    checkEnvironment,
    getSystemInfo,
    checkDependencies,
    installDependencies,
    install,
    getInstallStream,
    // wizard-friendly helpers
    checkSystem,
    createAdmin,
    saveSiteSettings,
    finishOOBE
  }
}
