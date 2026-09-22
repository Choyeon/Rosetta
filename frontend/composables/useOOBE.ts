import type { OOBEStatus, OOBEInstallRequest, TokenResponse } from '~~/types/api'
import { useAuthStore } from '~~/stores/auth'

type CheckLevel = 'ok' | 'warn' | 'err'

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
  onOpen?: () => void,
  opts?: {
    // R1-CEx-2: SSE 客户端空闲超时（毫秒）。超过此时长未收到任何 onmessage → 调 onIdleTimeout。
    idleTimeoutMs?: number
    onIdleTimeout?: () => void
    onError?: () => void
  }
): { close: () => void, reconnect: () => void, kickIdle: () => void } {
  let es: EventSource | null = null
  let closed = false
  let idleTimer: ReturnType<typeof setTimeout> | null = null
  const idleTimeoutMs = opts?.idleTimeoutMs ?? 0

  const clearIdle = () => {
    if (idleTimer) {
      clearTimeout(idleTimer)
      idleTimer = null
    }
  }
  const resetIdle = () => {
    if (!idleTimeoutMs) return
    clearIdle()
    idleTimer = setTimeout(() => {
      try {
        opts?.onIdleTimeout?.()
      } catch {
        /* ignore */
      }
    }, idleTimeoutMs)
  }

  const open = () => {
    if (closed) return
    try {
      es = new EventSource(url)
      es.onopen = () => {
        resetIdle()
        onOpen?.()
      }
      es.onmessage = (e: MessageEvent) => {
        resetIdle()
        try {
          const parsed = JSON.parse(e.data)
          onEvent(parsed as T, e)
        } catch {
          /* ignore parse errors */
        }
      }
      es.addEventListener('connected', (e: Event) => {
        resetIdle()
        const me = e as MessageEvent
        try {
          const parsed = JSON.parse(me.data)
          onEvent({ type: 'connected', ...parsed } as T, me)
        } catch {
          /* ignore */
        }
      })
      es.onerror = () => {
        // 浏览器内置静默重试；此处额外 kick 一次 idle 以避免断连重连期时钟丢失。
        resetIdle()
        try {
          opts?.onError?.()
        } catch {
          /* ignore */
        }
      }
    } catch {
      /* ignore */
    }
  }

  open()

  return {
    close: () => {
      closed = true
      clearIdle()
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
    },
    kickIdle: resetIdle
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
  // shallowRef 而非 ref：ref<T>() 会把值类型套上 UnwrapRef<T>，
  // 与声明的返回类型 Ref<T | null> 不兼容；接口响应对象也不需要深层响应式。
  const data = shallowRef<T | null>(null)
  const error = shallowRef<{ status?: number, statusText?: string, message?: string } | null>(null)

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

    // 同 useApi.ts：开放泛型下 $fetch<T> 显式泛型会让 Nitro 路由条件类型栈溢出（TS2321），
    // 将 $fetch 擦除为普通函数类型彻底断开推断链。
    const _fetch = $fetch as unknown as (
      url: string,
      opts?: Record<string, unknown>
    ) => Promise<unknown>
    const request = _fetch(target, {
      method,
      body: body ? JSON.stringify(body) : undefined,
      headers
    }) as Promise<T>

    request
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

const OOBE_API_BASE_STORAGE_KEY = 'rosetta:oobe:apiBase'

/**
 * 规范化用户填入的后端地址：
 *   - 空串 → 返回默认同源 /api
 *   - 纯 host:port（无协议、无斜杠开头、也不是 /api）→ 补 "http://" + 末尾补 "/api"（最常见场景："127.0.0.1:8000" → "http://127.0.0.1:8000/api"）
 *   - 以 host:port/path 开头但 path!=/api → 末尾追 "/api"
 *   - 已有协议 + 完整 URL → 去结尾多余 "/api/api"，去结尾斜杠
 *   - 仅 "/api" → 返回 "/api"
 */
export function normalizeUserApiBase(input: unknown): string {
  let s = typeof input === 'string' ? input.trim() : ''
  if (!s) return '/api'
  // 纯相对路径 (Nginx/同源部署) → 保留，但清理重复前缀
  if (s.startsWith('/')) {
    s = s.replace(/\/{2,}/g, '/')
    if (!s.startsWith('/api')) s = s === '/' ? '/api' : `/api${s.replace(/^\/api\/?/, '')}`
    // 清除重复 /api/api/..
    while (/^\/api\/api(\b|\/)/.test(s)) s = s.replace(/^\/api\/api/, '/api')
    return s.replace(/\/+$/, '') || '/api'
  }
  // 缺协议：补 http://
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(s)) s = `http://${s}`
  try {
    const u = new URL(s, 'http://placeholder.invalid')
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return s.replace(/\/+$/, '')
    let p = u.pathname.replace(/\/{2,}/g, '/').replace(/\/+$/, '')
    // 末尾路径不是 /api → 补 /api
    if (!/\/api$/.test(p)) {
      if (p === '' || p === '/') p = '/api'
      else if (/\/api\/.+$/.test(p)) {
        // /api/something 保留
      } else {
        p = `${p.replace(/\/api\/?$/, '')}/api`
      }
    }
    // 去 /api/api/..
    while (/\/api\/api(\b|\/)/.test(p)) p = p.replace(/^\/api\/api/, '/api')
    const port = u.port ? `:${u.port}` : ''
    return `${u.protocol}//${u.hostname}${port}${p || '/api'}`
  } catch {
    // 非法 URL 结构：简单去尾部
    return s.replace(/\/+$/, '')
  }
}

function readOOBEApiBaseOverrideFromStorage(): string | null {
  try {
    if (typeof localStorage === 'undefined') return null
    const raw = localStorage.getItem(OOBE_API_BASE_STORAGE_KEY)
    if (!raw) return null
    const v = JSON.parse(raw) as unknown
    if (typeof v === 'string') {
      const cleaned = normalizeUserApiBase(v)
      return cleaned || null
    }
    return null
  } catch {
    return null
  }
}

function writeOOBEApiBaseOverrideToStorage(v: string) {
  try {
    if (typeof localStorage === 'undefined') return
    localStorage.setItem(OOBE_API_BASE_STORAGE_KEY, JSON.stringify(v))
  } catch { /* quota / SSR safety ignore */ }
}

export function clearOOBEApiBaseOverrideFromStorage() {
  try {
    if (typeof localStorage === 'undefined') return
    localStorage.removeItem(OOBE_API_BASE_STORAGE_KEY)
  } catch { /* ignore */ }
}

export const useOOBE = () => {
  // ==========================================================
  // setup 顶层：一次性调用所有 composables，拿到引用
  // ==========================================================
  const authStore = useAuthStore()
  const runtimeConfig = useRuntimeConfig()
  // 向导期间允许用户临时覆盖：localStorage rosetta:oobe:apiBase → runtimeConfig.public.apiBase
  const overrideApiBase = ref<string | null>(null)
  const effectiveApiBase = computed<string>(() => {
    const user = overrideApiBase.value || readOOBEApiBaseOverrideFromStorage()
    if (user) return normalizeUserApiBase(user)
    return normalizeUserApiBase(String(runtimeConfig.public.apiBase || '/api'))
  })
  function currentApiBase() {
    return effectiveApiBase.value
  }
  const { locale } = useI18n()

  const status = ref<OOBEStatus | null>(null)
  const loading = ref(false)
  const error = ref<unknown>(null)
  const systemChecks = ref<SystemCheckRow[]>([])
  const systemSummary = ref<SystemSummary | null>(null)
  // R1-CEx-2: SSE 兜底快照状态（对外暴露给 UI 以渲染 Cancel/Retry 按钮）
  const installSnapshotState = ref<'idle' | 'timeout' | 'polling' | 'retrying'>('idle')
  // R1-CEx-2: UI 主动取消 SSE 订阅/安装观察的回调（由 finishOOBE 在订阅时注入）
  let _cancelInstallWatchFn: null | (() => void) = null

  /**
   * 用户在 Step1 点"应用"或探测成功后，调用本函数：
   *  1) 规范化 apiBase
   *  2) 写入本 composable override 变量 & localStorage，使后续所有 request / SSE 立即切到用户指定后端
   *  返回规范化后的字符串
   */
  const setBackendApiBase = (raw: string | undefined | null): string => {
    const normalized = normalizeUserApiBase(raw)
    overrideApiBase.value = normalized
    writeOOBEApiBaseOverrideToStorage(normalized)
    return normalized
  }

  const probeBackend = async (
    candidate: unknown,
    opts?: { timeoutMs?: number, locale?: string }
  ): Promise<{
    ok: boolean
    code: number
    statusText: string
    apiBase: string
    stage: 'health' | 'status'
    errorCode?: string
    detail?: string
    healthJson?: Record<string, unknown>
    statusJson?: Record<string, unknown>
    oobeRequired?: boolean
    oobeComplete?: boolean
  }> => {
    const api = normalizeUserApiBase(candidate as string)
    const timeout = typeof opts?.timeoutMs === 'number' ? opts.timeoutMs : 5000
    const loc = opts?.locale || locale.value
    const headers: Record<string, string> = { Accept: 'application/json' }
    if (loc) headers['Accept-Language'] = loc
    // 1) 先探 /health（FastAPI 裸端点，不在 /api 下，需要剥离 /api 后缀拼 URL）
    // eslint-disable-next-line no-useless-assignment
    let healthCode = 0
    // eslint-disable-next-line no-useless-assignment
    let healthStatusText = ''
    let healthJson: Record<string, unknown> | undefined
    try {
      const stripApi = api.endsWith('/api') ? api.slice(0, -4) : api
      const base = stripApi.replace(/\/+$/, '') || api
      const target = /^https?:\/\//i.test(base) ? `${base}/health` : `${base}/health`
      // 如果 base 是同源 /api（无协议），走浏览器相对 /health
      let finalTarget: string
      if (/^https?:\/\//i.test(target)) finalTarget = target
      else if (target.startsWith('/health')) finalTarget = target
      else finalTarget = `/health${target.startsWith('/') ? target : `/${target}`}`
      const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null
      const timer = ctrl ? setTimeout(() => ctrl.abort(), timeout) : null
      try {
        const r = await $fetch.raw<Record<string, unknown> | string>(finalTarget, {
          headers,
          signal: ctrl?.signal,
          timeout,
          credentials: 'omit',
          ignoreResponseError: true
        })
        healthCode = r.status ?? 200
        healthStatusText = r.statusText || (healthCode === 200 ? 'OK' : 'Fail')
        if (r._data && typeof r._data === 'object' && r._data !== null) {
          healthJson = r._data as Record<string, unknown>
        }
      } finally {
        if (timer) clearTimeout(timer)
      }
    } catch (e: unknown) {
      const err = e as { status?: number, statusText?: string, message?: string }
      healthCode = err.status ?? 0
      healthStatusText = err.statusText || (err.message || '连接失败')
    }
    if (healthCode !== 200 || (healthJson && healthJson.status && healthJson.status !== 'healthy')) {
      return {
        ok: false,
        code: healthCode,
        statusText: healthStatusText || (healthCode === 0 ? '不可达' : '非 200'),
        apiBase: api,
        stage: 'health',
        detail: `/health 返回 ${healthCode}${healthJson ? `：${JSON.stringify(healthJson)}` : ''}`
      }
    }
    // 2) 再探 /api/oobe/status；允许 503 OOBE_REQUIRED（这才是正常的"未安装"态）
    // eslint-disable-next-line no-useless-assignment
    let statusCode = 0
    let statusJson: Record<string, unknown> | undefined
    let statusText = ''
    try {
      const target = /^https?:\/\//i.test(api) ? `${api}/oobe/status` : `${api}/oobe/status`
      const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null
      const timer = ctrl ? setTimeout(() => ctrl.abort(), timeout) : null
      try {
        const r = await $fetch.raw<Record<string, unknown>>(target, {
          headers: { ...headers, 'Content-Type': 'application/json' },
          signal: ctrl?.signal,
          timeout,
          credentials: 'omit',
          ignoreResponseError: true
        })
        statusCode = r.status ?? 200
        if (r._data && typeof r._data === 'object' && r._data !== null) {
          statusJson = r._data as Record<string, unknown>
        }
      } finally {
        if (timer) clearTimeout(timer)
      }
    } catch (e: unknown) {
      const err = e as { status?: number, statusText?: string, data?: unknown, message?: string }
      statusCode = err.status ?? 0
      statusText = err.statusText || err.message || ''
      if (err.data && typeof err.data === 'object') statusJson = err.data as Record<string, unknown>
    }
    const data = statusJson || {}
    const successJson = data.success === true
    const oobeComplete = Boolean(data.oobe_complete)
    const ec = typeof data.error_code === 'string' ? data.error_code : ''
    const oobeRequired = statusCode === 503 && ec === 'OOBE_REQUIRED'
    const ok = Boolean(
      (statusCode === 200 && successJson)
      || oobeRequired
    )
    return {
      ok,
      code: statusCode,
      statusText: statusText || (statusCode === 0 ? '不可达' : `${statusCode}`),
      apiBase: api,
      stage: 'status',
      errorCode: ec || undefined,
      healthJson,
      statusJson,
      oobeRequired,
      oobeComplete
    }
  }

  // ----------------------------------------------------------
  // 简单 API 包装（setup 之后任何地方都可调用）
  // ----------------------------------------------------------
  const getOOBEStatus = async () => {
    const result = await request<OOBEStatus & { success?: boolean }>('/oobe/status', {
      authStore, apiBase: currentApiBase(), locale: locale.value
    })
    if (!result.error.value) status.value = (result.data.value ?? null) as OOBEStatus
    return result
  }

  const checkEnvironment = async () => {
    return request<Record<string, RawCheckResult>>('/oobe/check', {
      authStore, apiBase: currentApiBase(), locale: locale.value
    })
  }

  const getSystemInfo = async () => {
    return request<Record<string, unknown>>('/oobe/system-info', {
      authStore, apiBase: currentApiBase(), locale: locale.value
    })
  }

  const checkDependencies = async () => {
    return request<Record<string, unknown>>('/oobe/dependencies', {
      authStore, apiBase: currentApiBase(), locale: locale.value
    })
  }

  const installDependencies = async () => {
    return request<Record<string, unknown>>('/oobe/install-dependencies', {
      authStore, apiBase: currentApiBase(), locale: locale.value, method: 'POST'
    })
  }

  /**
   * 订阅依赖安装 SSE 日志流（对标 WordPress 一键安装实时进度）
   */
  const subscribeDependencyStream = (
    sid: string,
    onEvent: (evt: DepProgressEvt) => void
  ) => {
    const base = currentApiBase()
    const full = /^https?:\/\//.test(base)
      ? `${base}/oobe/install-dependencies/stream?sid=${encodeURIComponent(sid)}`
      : `${base}/oobe/install-dependencies/stream?sid=${encodeURIComponent(sid)}`
    return connectSSE<DepProgressEvt>(full, evt => onEvent(evt))
  }

  const install = async (body: OOBEInstallRequest) => {
    return request<Record<string, unknown>>('/oobe/install', {
      authStore, apiBase: currentApiBase(), locale: locale.value, method: 'POST', body
    })
  }

  const getInstallStream = (sid: string) => {
    const base = currentApiBase()
    return new EventSource(`${base}/oobe/install/stream?sid=${sid}`)
  }

  /**
   * 订阅一键安装 SSE 进度流
   * R1-CEx-2: 暴露 idleTimeoutMs / onIdleTimeout 给调用方，
   * 以便在 30s 无 SSE 消息时执行快照兜底轮询。
   */
  const subscribeInstallStream = (
    sid: string,
    onEvent: (evt: InstallProgressEvt) => void,
    opts?: { idleTimeoutMs?: number, onIdleTimeout?: () => void, onError?: () => void }
  ) => {
    const base = currentApiBase()
    const url = `${base}/oobe/install/stream?sid=${encodeURIComponent(sid)}`
    return connectSSE<InstallProgressEvt>(url, evt => onEvent(evt), undefined, opts)
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
    onProgress?: (evt: InstallProgressEvt) => void,
    opts?: {
      // UI 主动取消当前安装观察的句柄注入（UI 层调用 cancelInstallWatch 会触发）
      onCancelRequested?: (resolvers: {
        cancelSSE: () => void
        setInstallingFalse: () => void
      }) => void
    }
  ) => {
    loading.value = true
    error.value = null
    installSnapshotState.value = 'idle'
    let streamHandle: { close: () => void } | null = null
    let cancelled = false
    let pollTimer: ReturnType<typeof setTimeout> | null = null
    let resolvedOnce = false

    // cleanup：统一释放 SSE + 轮询定时器，避免泄漏
    const cleanupAll = () => {
      if (streamHandle) {
        streamHandle.close()
        streamHandle = null
      }
      if (pollTimer) {
        clearTimeout(pollTimer)
        pollTimer = null
      }
      _cancelInstallWatchFn = null
    }

    // 暴露给 UI 的取消接口：仅取消"前端安装观察"，不影响后端已提交请求（后端有幂等锁）
    _cancelInstallWatchFn = () => {
      if (resolvedOnce) return
      cancelled = true
      cleanupAll()
      opts?.onCancelRequested?.({
        cancelSSE: () => {},
        setInstallingFalse: () => {}
      })
    }

    // R1-CEx-2: 快照 reconciliation —— 调 getOOBEStatus，根据结果合成 done/error/继续轮询
    const tryReconcile = async (): Promise<'done' | 'retry' | 'failed'> => {
      try {
        const res = await getOOBEStatus()
        const payload = (res?.data?.value ?? {}) as { oobe_complete?: boolean, initialized?: boolean }
        if (payload.oobe_complete === true || payload.initialized === true) {
          return 'done'
        }
        if (res.error.value && res.error.value.status === 409) {
          // 后端显式返回 ALREADY_COMPLETED
          return 'done'
        }
        return 'retry'
      } catch {
        return 'retry'
      }
    }

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
      // OOBE 路由固定 ssr:false → 必然运行在浏览器内，location 一定存在
      if (!siteUrl && typeof location !== 'undefined') {
        siteUrl = location.origin
      }
      if (!siteUrl) {
        const cfgSiteUrl = String(useRuntimeConfig().public.siteUrl || '').trim()
        if (cfgSiteUrl) siteUrl = cfgSiteUrl
      }

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

      // R1-CEx-2: idleTimeout 30s → 快照 reconciliation → 最多 3 次 5s 间隔轮询（总 45s）
      let pollAttempts = 0
      const MAX_POLL_ATTEMPTS = 3
      const POLL_INTERVAL_MS = 5000

      const scheduleNextPoll = () => {
        if (resolvedOnce || cancelled) return
        pollAttempts += 1
        installSnapshotState.value = 'polling'
        onProgress?.({ type: 'progress', step_id: 'finalize', percent: 99, message: 'SSE 暂无事件，正在轮询安装最终状态…' })
        pollTimer = setTimeout(async () => {
          if (resolvedOnce || cancelled) return
          const stNow = await tryReconcile()
          if (stNow === 'done') {
            onProgress?.({ type: 'done', success: true })
          } else if (pollAttempts < MAX_POLL_ATTEMPTS) {
            scheduleNextPoll()
          } else {
            // 45s 总兜底仍未收敛 → 抛 error 交给 UI 显示 Retry 按钮（installing 必须解除）
            installSnapshotState.value = 'retrying'
            onProgress?.({ type: 'error', success: false, message: '安装状态无法确认，请点重试或手动检查后端。' })
          }
        }, POLL_INTERVAL_MS)
      }

      const onIdleTimeout = () => {
        if (resolvedOnce || cancelled) return
        installSnapshotState.value = 'timeout'
        // 立即一次 reconciliation；若未完成则开始轮询
        void (async () => {
          if (resolvedOnce || cancelled) return
          const stNow = await tryReconcile()
          if (stNow === 'done') {
            onProgress?.({ type: 'done', success: true })
          } else {
            scheduleNextPoll()
          }
        })()
      }

      if (onProgress) {
        streamHandle = subscribeInstallStream(sid, (evt) => {
          // 收到 SSE 事件时若处于 timeout/polling → 恢复正常态
          if (evt.type === 'progress' || evt.type === 'done' || evt.type === 'error') {
            if (installSnapshotState.value !== 'idle') installSnapshotState.value = 'idle'
          }
          if (evt.type === 'done' || evt.type === 'error') resolvedOnce = true
          onProgress(evt)
        }, { idleTimeoutMs: 30_000, onIdleTimeout })
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
        if (cancelled) break
        try {
          const { data: loginData, error: loginErr } = await request<TokenResponse>('/users/login', {
            method: 'POST',
            body: {
              username: adminUser.username,
              password: adminUser.password
            },
            authStore,
            apiBase: currentApiBase(),
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
      cleanupAll()
      if (!resolvedOnce) installSnapshotState.value = 'idle'
    }
  }

  /**
   * R1-CEx-2: UI 层主动取消安装观察。
   * 注意：后端 install 请求在 FastAPI 内已持有 asyncio.Lock 且写 OOBE_LOCK 文件，
   * 前端取消不会中断后端写入，仅解除 UI installing 假死。
   */
  const cancelInstallWatch = () => {
    if (_cancelInstallWatchFn) {
      _cancelInstallWatchFn()
      _cancelInstallWatchFn = null
    }
    installSnapshotState.value = 'idle'
  }

  return {
    // state
    status,
    loading,
    error,
    systemChecks,
    systemSummary,
    // R1-CEx-2: SSE 超时 / 轮询状态 + UI 主动取消
    installSnapshotState,
    cancelInstallWatch,
    // backend connection (O series Step1)
    effectiveApiBase,
    setBackendApiBase,
    probeBackend,
    normalizeUserApiBase,
    clearOOBEApiBaseOverrideFromStorage,
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
