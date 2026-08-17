import type { OOBEStatus, OOBEInstallRequest, TokenResponse } from '~~/types/api'
import { useAuthStore } from '~~/stores/auth'

type CheckLevel = 'ok' | 'warn' | 'err'
interface SystemCheckRow {
  name: string
  detail: string
  status: CheckLevel
  statusText: string
}

export interface DepProgressEvt {
  type: 'progress' | 'log' | 'done' | 'connected'
  name?: string
  status?: string
  message?: string
  success?: boolean
  summary?: Record<string, unknown>
  sid?: string
  buffered?: number
  timestamp?: string
}

export interface InstallProgressEvt {
  type: 'progress' | 'done' | 'error' | 'connected'
  step_id?: string
  message?: string
  percent?: number
  success?: boolean
  frontend_url?: string
  admin_url?: string
  traceback?: string
  sid?: string
  buffered?: number
  timestamp?: string
}

interface RawCheckResult {
  ok?: unknown
  error?: unknown
  value?: unknown
  display?: unknown
  os_summary?: unknown
  cpu_count?: unknown
  arch?: unknown
  total_gb?: unknown
  avail_gb?: unknown
  total_mb?: unknown
  used_mb?: unknown
  used_gb?: unknown
  usage_pct?: unknown
  path?: unknown
}

function levelize(raw: RawCheckResult | null | undefined): { level: CheckLevel, text: string, detail: string } {
  if (!raw || typeof raw !== 'object') {
    return { level: 'err', text: '未知', detail: '无法解析检测结果' }
  }
  const ok = Boolean(raw.ok)
  const error = raw.error ? String(raw.error) : ''
  // 问题4：后端丰富化后优先用 display 人类可读字符串（带 GB 单位）
  const display = raw.display ? String(raw.display) : ''
  const value = raw.value !== undefined && raw.value !== null ? String(raw.value) : ''
  if (ok) {
    return {
      level: 'ok',
      text: '通过',
      // 优先显示 display（带单位/总量/使用率），否则 fallback 到 value 或 error
      detail: display || (error ? `${error}` : value || '检测通过')
    }
  }
  // 失败时：如果后端给了 display 仍然显示（例如内存偏低时仍显示"可用 X GB / 总量 Y GB"）
  const base = error ? error : (display || value || '未安装 / 未连接')
  return {
    level: error ? 'warn' : 'warn',
    text: error ? '警告' : '跳过',
    detail: base
  }
}

export interface SystemSummary {
  osName: string
  osVersion: string
  osType: string
  processor: string
  architecture: string
  pythonVersion: string
  pythonPath: string
  cpuCount: number
  totalMemoryGB: string
  availableMemoryGB: string
  totalDiskGB: string
  freeDiskGB: string
  hostname: string
}

export interface SystemCheckRow {
  name: string
  detail: string
  status: CheckLevel
  statusText: string
  osSummary?: string
  extra?: Record<string, string | number>
}

function connectSSE<T extends object>(
  url: string,
  onEvent: (evt: T, raw: MessageEvent) => void,
  onOpen?: () => void
): { close: () => void, reconnect: () => void } {
  let es: EventSource | null = null
  let closed = false

  const open = () => {
    if (closed) return
    try {
      es = new EventSource(url)
      es.onopen = () => onOpen?.()
      es.onmessage = (e: MessageEvent) => {
        try {
          const parsed = JSON.parse(e.data)
          onEvent(parsed as T, e)
        } catch {
          /* ignore parse errors */
        }
      }
      es.addEventListener('connected', (e: Event) => {
        const me = e as MessageEvent
        try {
          const parsed = JSON.parse(me.data)
          onEvent({ type: 'connected', ...parsed } as T, me)
        } catch {
          /* ignore */
        }
      })
      es.onerror = () => {
        /* SSE 连接失败静默重试（浏览器内置） */
      }
    } catch {
      /* ignore */
    }
  }

  open()

  return {
    close: () => {
      closed = true
      if (es) {
        es.close()
        es = null
      }
    },
    reconnect: () => {
      if (es) {
        es.close()
        es = null
      }
      open()
    }
  }
}

/**
 * 统一 API 调用包装：使用 $fetch 代替 useFetch
 * $fetch 可以在任何上下文（setup/onMounted/handler）中安全调用
 */
function request<T = unknown>(
  url: string,
  opts: {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
    body?: unknown
    params?: Record<string, unknown>
    timeoutMs?: number
    authStore: ReturnType<typeof useAuthStore>
    apiBase: string
    locale?: string
  }
): Promise<{ data: Ref<T | null>, error: Ref<{ status?: number, statusText?: string, message?: string } | null> }> {
  const { authStore, apiBase, method = 'GET', body, params, timeoutMs, locale } = opts
  const data = ref<T | null>(null)
  const error = ref<{ status?: number, statusText?: string, message?: string } | null>(null)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
  if (authStore.accessToken) {
    headers.Authorization = `Bearer ${authStore.accessToken}`
  }
  if (locale) {
    headers['Accept-Language'] = locale
  }

  // 简单拼接：相对 apiBase（如 /api）直接前置；绝对 apiBase 直接拼接 URL
  const normalizedApi = apiBase.endsWith('/') ? apiBase.slice(0, -1) : apiBase
  const normalizedUrl = url.startsWith('/') ? url : `/${url}`
  let target: string
  if (/^https?:\/\//i.test(normalizedApi)) {
    target = `${normalizedApi}${normalizedUrl}`
  } else {
    target = `${normalizedApi}${normalizedUrl}`
  }
  if (params) {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) qs.set(k, String(v))
    })
    const qsStr = qs.toString()
    if (qsStr) target += (target.includes('?') ? '&' : '?') + qsStr
  }

  return new Promise((resolve) => {
    let cancelled = false
    const timer = timeoutMs
      ? setTimeout(() => {
          cancelled = true
          error.value = { status: 0, statusText: 'Timeout', message: 'Request timed out' }
          resolve({ data, error })
        }, timeoutMs)
      : null

    $fetch<T>(target, {
      method,
      body: body ? JSON.stringify(body) : undefined,
      headers
    })
      .then((res) => {
        if (cancelled) return
        // 后端返回两种格式：
        // 1. 包装型：{ success: boolean, data?: T, message?: string, ... }
        // 2. 扁平型（OOBE接口）：{ success: true, python_version: {...}, uv_installed: {...}, ... }
        const env = res as unknown as Record<string, unknown>
        if (env && typeof env === 'object' && 'success' in env) {
          if (env.data !== undefined && env.data !== null) {
            data.value = env.data as T | null
          } else {
            // 去掉 success 外壳，返回实际检测结果
            const copy = { ...env }
            delete copy.success
            delete copy.message
            delete copy.error_code
            delete copy.errors
            data.value = copy as unknown as T
          }
        } else {
          data.value = res
        }
      })
      .catch((err: { status?: number, statusText?: string, data?: unknown, message?: string }) => {
        if (cancelled) return
        error.value = {
          status: err.status ?? 0,
          statusText: err.statusText ?? 'Network Error',
          message: typeof err.data === 'string' ? err.data : err.message
        }
      })
      .finally(() => {
        if (timer) clearTimeout(timer)
        resolve({ data, error })
      })
  })
}

export const useOOBE = () => {
  // ==========================================================
  // setup 顶层：一次性调用所有 composables，拿到引用
  // ==========================================================
  const authStore = useAuthStore()
  const runtimeConfig = useRuntimeConfig()
  const apiBase = runtimeConfig.public.apiBase || '/api'
  const { locale } = useI18n()

  const status = ref<OOBEStatus | null>(null)
  const loading = ref(false)
  const error = ref<unknown>(null)
  const systemChecks = ref<SystemCheckRow[]>([])
  const systemSummary = ref<SystemSummary | null>(null)

  // ----------------------------------------------------------
  // 简单 API 包装（setup 之后任何地方都可调用）
  // ----------------------------------------------------------
  const getOOBEStatus = async () => {
    const result = await request<OOBEStatus & { success?: boolean }>('/oobe/status', {
      authStore, apiBase, locale: locale.value
    })
    if (!result.error.value) status.value = (result.data.value ?? null) as OOBEStatus
    return result
  }

  const checkEnvironment = async () => {
    return request<Record<string, RawCheckResult>>('/oobe/check', {
      authStore, apiBase, locale: locale.value
    })
  }

  const getSystemInfo = async () => {
    return request<Record<string, unknown>>('/oobe/system-info', {
      authStore, apiBase, locale: locale.value
    })
  }

  const checkDependencies = async () => {
    return request<Record<string, unknown>>('/oobe/dependencies', {
      authStore, apiBase, locale: locale.value
    })
  }

  const installDependencies = async () => {
    return request<Record<string, unknown>>('/oobe/install-dependencies', {
      authStore, apiBase, locale: locale.value, method: 'POST'
    })
  }

  /**
   * 订阅依赖安装 SSE 日志流（对标 WordPress 一键安装实时进度）
   */
  const subscribeDependencyStream = (
    sid: string,
    onEvent: (evt: DepProgressEvt) => void
  ) => {
    const base = apiBase
    const full = /^https?:\/\//.test(base)
      ? `${base}/oobe/install-dependencies/stream?sid=${encodeURIComponent(sid)}`
      : `${base}/oobe/install-dependencies/stream?sid=${encodeURIComponent(sid)}`
    return connectSSE<DepProgressEvt>(full, evt => onEvent(evt))
  }

  const install = async (body: OOBEInstallRequest) => {
    return request<Record<string, unknown>>('/oobe/install', {
      authStore, apiBase, locale: locale.value, method: 'POST', body
    })
  }

  const getInstallStream = (sid: string) => {
    const base = apiBase
    return new EventSource(`${base}/oobe/install/stream?sid=${sid}`)
  }

  /**
   * 订阅一键安装 SSE 进度流
   */
  const subscribeInstallStream = (
    sid: string,
    onEvent: (evt: InstallProgressEvt) => void
  ) => {
    const base = apiBase
    const url = `${base}/oobe/install/stream?sid=${encodeURIComponent(sid)}`
    return connectSSE<InstallProgressEvt>(url, evt => onEvent(evt))
  }

  // -------- 向导友好的封装 --------
  const checkSystem = async (): Promise<SystemCheckRow[]> => {
    loading.value = true
    error.value = null
    try {
      // 并行调用环境检测 + 系统摘要，减少等待
      const [envResult, sysInfoResult] = await Promise.all([
        checkEnvironment(),
        getSystemInfo()
      ])
      const err = envResult.error.value
      // 问题4：填充更丰富系统摘要给 Step1 顶部展示
      if (!sysInfoResult.error.value && sysInfoResult.data.value) {
        const raw = sysInfoResult.data.value as Record<string, unknown>
        const toGB = (mbOrGb: unknown, isMB = true) => {
          if (mbOrGb === undefined || mbOrGb === null) return '?'
          const num = Number(mbOrGb)
          if (Number.isNaN(num)) return String(mbOrGb)
          // isMB=true 且数值 >= 500 当作 MB 转 GB；否则直接当 GB
          const gb = isMB && num >= 500 ? num / 1024 : num
          return `${gb.toFixed(1)} GB`
        }
        systemSummary.value = {
          osName: String(raw.os_name ?? ''),
          osVersion: String(raw.os_version ?? ''),
          osType: String(raw.os_type ?? ''),
          processor: String(raw.processor ?? ''),
          architecture: String(raw.architecture ?? ''),
          pythonVersion: String(raw.python_version ?? ''),
          pythonPath: String(raw.python_path ?? ''),
          cpuCount: Number(raw.cpu_count ?? 1) || 1,
          totalMemoryGB: toGB(raw.total_memory_mb),
          availableMemoryGB: toGB(raw.available_memory_mb),
          totalDiskGB: toGB(raw.disk_total_gb, false),
          freeDiskGB: toGB(raw.disk_free_gb, false),
          hostname: String(raw.hostname ?? '')
        }
      }

      if (err) {
        systemChecks.value = [
          {
            name: '后端 API 连接',
            detail: `${err?.status || 0} ${err?.statusText || 'Network Error'} — 请确认端口 8000 的后端服务可用`,
            status: 'warn',
            statusText: '警告'
          }
        ]
        return systemChecks.value
      }
      interface EnvCheckResponse {
        python_version?: RawCheckResult
        uv_installed?: RawCheckResult
        uv_version?: RawCheckResult
        node_version?: RawCheckResult
        pnpm_version?: RawCheckResult
        database_connectivity?: RawCheckResult
        redis_connectivity?: RawCheckResult
        disk_free_gb?: RawCheckResult
        memory_free_mb?: RawCheckResult
        [k: string]: RawCheckResult | undefined
      }
      const raw = (envResult.data.value as EnvCheckResponse) || ({} as EnvCheckResponse)
      const make = (name: string, value: RawCheckResult | undefined, fallback?: RawCheckResult) => {
        const src: RawCheckResult = (fallback ?? value) ?? {}
        const info = levelize(src)
        const row: SystemCheckRow = {
          name,
          detail: info.detail,
          status: info.level as CheckLevel,
          statusText: info.text
        }
        // 把后端附加的丰富信息（os_summary/cpu_count/usage_pct 等）带过来
        if (typeof src.os_summary === 'string') row.osSummary = src.os_summary
        const extraKeys = ['cpu_count', 'arch', 'total_gb', 'avail_gb', 'total_mb', 'used_mb', 'used_gb', 'usage_pct', 'path'] as const
        for (const k of extraKeys) {
          if (src[k] !== undefined && src[k] !== null) {
            row.extra = row.extra ?? {}
            row.extra[k] = src[k] as string | number
          }
        }
        systemChecks.value.push(row)
      }
      systemChecks.value = []
      make('Python 解释器', raw.python_version)
      make(
        'uv 包管理器',
        raw.uv_installed,
        {
          ok: raw.uv_installed?.ok ?? false,
          value: (raw.uv_version as RawCheckResult | undefined)?.value,
          error: (raw.uv_installed as RawCheckResult | undefined)?.error
        }
      )
      make('Node.js', raw.node_version)
      make('pnpm', raw.pnpm_version)
      make('数据库连接', raw.database_connectivity)
      make('Redis 连接', raw.redis_connectivity)
      make('剩余磁盘空间', raw.disk_free_gb)
      make('空闲内存', raw.memory_free_mb)
      status.value = {
        ...(status.value as OOBEStatus ?? {}),
        systemChecks: systemChecks.value
      } as OOBEStatus & { systemChecks: SystemCheckRow[] }
      return systemChecks.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  const createAdmin = async (payload: {
    username: string
    email: string
    password: string
    nickname?: string
    bio?: string
  }) => {
    loading.value = true
    error.value = null
    try {
      status.value = {
        ...(status.value as OOBEStatus ?? {}),
        adminCreated: true,
        adminUser: payload
      } as OOBEStatus & { adminCreated: boolean, adminUser: typeof payload }
      return status.value
    } finally {
      loading.value = false
    }
  }

  const saveSiteSettings = async (settings: {
    siteName: string
    description: string
    defaultLocale: string
    seoKeywords: string
    siteUrl?: string
    databaseType?: 'sqlite' | 'postgresql'
    dbHost?: string
    dbPort?: number
    dbName?: string
    dbUser?: string
    dbPassword?: string
    dbPath?: string
    redisEnabled?: boolean
    redisHost?: string
    redisPort?: number
    redisPassword?: string
    environment?: 'development' | 'production'
    enableComments?: boolean
    enableRegistration?: boolean
    enableRss?: boolean
    enableBingWallpaper?: boolean
    enablePagefindSearch?: boolean
    enableEncryptedPosts?: boolean
    enableMusicPlayer?: boolean
  }) => {
    loading.value = true
    error.value = null
    try {
      status.value = {
        ...(status.value as OOBEStatus ?? {}),
        siteConfigured: true,
        siteSettings: settings
      } as OOBEStatus & { siteConfigured: boolean, siteSettings: typeof settings }
      return status.value
    } finally {
      loading.value = false
    }
  }

  const finishOOBE = async (
    onProgress?: (evt: InstallProgressEvt) => void
  ) => {
    loading.value = true
    error.value = null
    let streamHandle: { close: () => void } | null = null
    try {
      interface OOBESiteSettings {
        siteUrl?: string
        siteName?: string
        description?: string
        defaultLocale?: string
        seoKeywords?: string
        databaseType?: 'sqlite' | 'postgresql'
        dbHost?: string
        dbPort?: number
        dbName?: string
        dbUser?: string
        dbPassword?: string
        dbPath?: string
        redisEnabled?: boolean
        redisHost?: string
        redisPort?: number
        redisPassword?: string
        environment?: 'development' | 'production'
        enableComments?: boolean
        enableRegistration?: boolean
        enableRss?: boolean
        enableBingWallpaper?: boolean
        enablePagefindSearch?: boolean
        enableEncryptedPosts?: boolean
        enableMusicPlayer?: boolean
      }
      interface OOBEAdminUser {
        username?: string
        email?: string
        password?: string
        nickname?: string
        bio?: string
      }
      const st = (status.value as
        OOBEStatus & { adminUser?: OOBEAdminUser, siteSettings?: OOBESiteSettings }
        ?? {})
      const adminUser: OOBEAdminUser = st.adminUser ?? {}
      const siteSettings: OOBESiteSettings = st.siteSettings ?? {}
      let siteUrl = (siteSettings.siteUrl ?? '').trim()
      if (!siteUrl && typeof location !== 'undefined') {
        siteUrl = location.origin
      }
      if (!siteUrl) siteUrl = 'http://localhost:3000'

      const author = adminUser.nickname ?? adminUser.username ?? ''
      const payload: OOBEInstallRequest & Record<string, unknown> = {
        database_type: siteSettings.databaseType ?? 'sqlite',
        db_host: siteSettings.dbHost ?? 'localhost',
        db_port: Number(siteSettings.dbPort) || 5432,
        db_name: siteSettings.dbName ?? 'rosetta',
        db_user: siteSettings.dbUser ?? '',
        db_password: siteSettings.dbPassword ?? '',
        db_path: siteSettings.dbPath ?? 'rosetta.db',
        redis_enabled: Boolean(siteSettings.redisEnabled),
        redis_host: siteSettings.redisHost ?? 'localhost',
        redis_port: Number(siteSettings.redisPort) || 6379,
        redis_password: siteSettings.redisPassword ?? '',

        admin_username: adminUser.username ?? '',
        admin_email: adminUser.email ?? '',
        admin_password: adminUser.password ?? '',
        admin_nickname: adminUser.nickname ?? adminUser.username ?? '',
        admin_bio: adminUser.bio ?? '',
        admin_github: '',
        admin_website: '',
        admin_avatar_source: 'auto',

        site_name: siteSettings.siteName ?? '',
        site_description: siteSettings.description ?? '',
        site_keywords: siteSettings.seoKeywords ?? '',
        site_url: siteUrl,
        site_author: author,
        site_email: adminUser.email ?? '',
        default_locale: siteSettings.defaultLocale ?? 'zh',

        enable_comments: siteSettings.enableComments ?? true,
        enable_registration: siteSettings.enableRegistration ?? false,
        enable_rss: siteSettings.enableRss ?? true,
        enable_bing_wallpaper: siteSettings.enableBingWallpaper ?? true,
        enable_pagefind_search: siteSettings.enablePagefindSearch ?? true,
        enable_encrypted_posts: siteSettings.enableEncryptedPosts ?? false,
        enable_music_player: siteSettings.enableMusicPlayer ?? true,
        environment: (siteSettings.environment as 'development' | 'production') || 'development'
      }

      const sid = Math.random().toString(36).slice(2) + Date.now().toString(36)
      if (onProgress) {
        streamHandle = subscribeInstallStream(sid, onProgress)
      }

      const { data, error: err } = await install(payload)
      if (err.value) throw err.value
      status.value = {
        ...(status.value as OOBEStatus ?? {}),
        initialized: true
      } as OOBEStatus & { initialized: boolean }

      // 自动登录新管理员
      const loginRetries = 6
      for (let i = 1; i <= loginRetries; i++) {
        try {
          const { data: loginData, error: loginErr } = await request<TokenResponse>('/users/login', {
            method: 'POST',
            body: {
              username: adminUser.username,
              password: adminUser.password
            },
            authStore,
            apiBase,
            locale: locale.value
          })
          if (!loginErr.value && loginData.value) {
            authStore.setTokens(loginData.value)
            await authStore.fetchUser()
            break
          }
          if (i === loginRetries) break
        } catch {
          // 继续重试
        }
        await new Promise(r => setTimeout(r, 1500))
      }

      return data.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
      if (streamHandle) streamHandle.close()
    }
  }

  return {
    // state
    status,
    loading,
    error,
    systemChecks,
    systemSummary,
    // raw AsyncData API
    getOOBEStatus,
    checkEnvironment,
    getSystemInfo,
    checkDependencies,
    installDependencies,
    subscribeDependencyStream,
    install,
    getInstallStream,
    subscribeInstallStream,
    // wizard-friendly helpers
    checkSystem,
    createAdmin,
    saveSiteSettings,
    finishOOBE
  }
}
