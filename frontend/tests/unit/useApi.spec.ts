import type { Ref } from 'vue'
import type { ApiUseFetchOptions } from '@/composables/useApi'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiFetch, silentApiFetch, useAPI } from '@/composables/useApi'

/**
 * apiFetch / silentApiFetch 组装后真实传给 $fetch 的选项形状
 * （见 composables/useApi.ts：timeout + 调用方 options + baseURL + headers）。
 */
interface CapturedFetchOptions {
  baseURL: string
  headers: Record<string, string>
  timeout?: number
  method?: string
  body?: unknown
  [k: string]: unknown
}

/** useAPI 传给 useFetch 的选项形状（headers 恒为 computed Ref）。 */
interface CapturedUseFetchOptions {
  key: string
  baseURL: string
  timeout: number
  headers: Ref<Record<string, string>>
  onRequest: (ctx: unknown) => unknown
  onResponse: (ctx: unknown) => unknown
  onResponseError: (ctx: { response: { status: number, _data?: unknown } }) => unknown
  [k: string]: unknown
}

/** $fetch 的 mock 签名：元组参数保证 calls[i][j] 取值有类型。 */
type FetchMockFn = (url: string, opts: CapturedFetchOptions) => Promise<unknown>

// —— 全部经 vi.hoisted 提前创建，供被提升的 vi.mock 工厂引用 ——
const mocks = vi.hoisted(() => ({
  fetchMock: vi.fn<FetchMockFn>(),
  navigateMock: vi.fn(async (..._args: unknown[]) => undefined),
  toastErrorMock: vi.fn(),
  refreshAccessTokenMock: vi.fn(async () => false),
  clearTokensMock: vi.fn(),
  authState: { accessToken: null as string | null, refreshToken: null as string | null },
  useFetchCaptured: null as CapturedUseFetchOptions | null
}))

vi.mock('vue-sonner', () => ({ toast: { error: mocks.toastErrorMock } }))

vi.mock('~~/stores/auth', () => ({
  useAuthStore: () => ({
    get accessToken() { return mocks.authState.accessToken },
    get refreshToken() { return mocks.authState.refreshToken },
    refreshAccessToken: mocks.refreshAccessTokenMock,
    clearTokens: mocks.clearTokensMock
  })
}))

// Nuxt 自动导入在编译期被改写为「按符号 from 具体模块」，逐个 mock 即可桩掉运行时
vi.mock('#app/nuxt', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return {
    ...actual,
    useRuntimeConfig: () => ({
      apiBase: 'http://127.0.0.1:8000/api',
      public: { apiBase: '/api' }
    }),
    useNuxtApp: () => ({ $i18n: { locale: { value: 'en' } } })
  }
})
vi.mock('#build/fetch.mjs', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return { ...actual, $fetch: mocks.fetchMock }
})
vi.mock('#app/composables/router', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return { ...actual, navigateTo: mocks.navigateMock }
})
vi.mock('#app/composables/fetch', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return {
    ...actual,
    useFetch: (_url: string, opts: CapturedUseFetchOptions) => {
      mocks.useFetchCaptured = opts
      return { data: { value: null } }
    }
  }
})

/** 构造一个带 status/data 的 fetch 失败对象（对齐 ofetch FetchError 形状）。 */
function fetchError(status: number, data?: unknown, message = 'http error') {
  return Object.assign(new Error(message), { status, data })
}

/** 取第 n 次 $fetch 调用的参数元组；没有该调用直接失败，绝不让 undefined 溜过断言。 */
function fetchCallAt(n: number): [string, CapturedFetchOptions] {
  const call = mocks.fetchMock.mock.calls[n]
  if (!call) throw new Error(`$fetch 未产生第 ${n + 1} 次调用`)
  return call
}

function lastFetchOptions(): CapturedFetchOptions {
  const calls = mocks.fetchMock.mock.calls
  return fetchCallAt(calls.length - 1)[1]
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.authState.accessToken = null
  mocks.authState.refreshToken = null
  mocks.useFetchCaptured = null
  mocks.refreshAccessTokenMock.mockResolvedValue(false)
  mocks.navigateMock.mockResolvedValue(undefined)
})

describe('useApi · apiFetch 请求契约', () => {
  it('成功请求：默认 15s 超时 + 客户端相对 baseURL + 语言/鉴权头', async () => {
    mocks.fetchMock.mockResolvedValue({ id: 1 })
    mocks.authState.accessToken = 'jwt-abc'

    const result = await apiFetch<{ id: number }>('/users/me')

    expect(result).toEqual({ id: 1 })
    const [url, opts] = fetchCallAt(0)
    expect(url).toBe('/users/me')
    expect(opts.timeout).toBe(15_000)
    expect(opts.baseURL).toBe('/api')
    expect(opts.headers['Accept-Language']).toBe('en')
    expect(opts.headers.Authorization).toBe('Bearer jwt-abc')
  })

  it('无 token 时不带 Authorization 头', async () => {
    mocks.fetchMock.mockResolvedValue(null)
    await apiFetch('/blog/posts')
    expect(lastFetchOptions().headers.Authorization).toBeUndefined()
  })

  it('FormData multipart 上传不套默认超时（防误杀大文件上传）', async () => {
    mocks.fetchMock.mockResolvedValue({ ok: true })
    const fd = new FormData()
    fd.append('file', new Blob(['x']), 'a.png')

    await apiFetch('/media/upload', { method: 'POST', body: fd })

    expect(lastFetchOptions().timeout).toBeUndefined()
  })

  it('JSON body 普通请求仍套 15s 默认超时', async () => {
    mocks.fetchMock.mockResolvedValue({})
    await apiFetch('/admin/settings', { method: 'PUT', body: { a: 1 } })
    expect(lastFetchOptions().timeout).toBe(15_000)
  })

  it('调用方显式 timeout 优先生效（含 FormData 场景）', async () => {
    mocks.fetchMock.mockResolvedValue({})
    await apiFetch('/x', { timeout: 5_000 })
    expect(lastFetchOptions().timeout).toBe(5_000)

    const fd = new FormData()
    fd.append('f', 'v')
    await apiFetch('/y', { method: 'POST', body: fd, timeout: 30_000 })
    expect(lastFetchOptions().timeout).toBe(30_000)
  })

  it('调用方 headers 与内置头合并', async () => {
    mocks.fetchMock.mockResolvedValue({})
    await apiFetch('/x', { headers: { 'X-Trace': '1' } })
    const h = lastFetchOptions().headers
    expect(h['X-Trace']).toBe('1')
    expect(h['Accept-Language']).toBe('en')
  })

  it('401：刷新成功 → 原请求自动重放一次并返回结果，不登出', async () => {
    mocks.fetchMock
      .mockRejectedValueOnce(fetchError(401, { error_code: 'TOKEN_EXPIRED' }))
      .mockResolvedValueOnce({ data: 'fresh' })
    mocks.refreshAccessTokenMock.mockResolvedValue(true)

    const result = await apiFetch<{ data: string }>('/admin/stats')

    expect(result).toEqual({ data: 'fresh' })
    expect(mocks.refreshAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(mocks.fetchMock).toHaveBeenCalledTimes(2)
    expect(mocks.clearTokensMock).not.toHaveBeenCalled()
    expect(mocks.navigateMock).not.toHaveBeenCalled()
    expect(mocks.toastErrorMock).not.toHaveBeenCalled()
  })

  it('401：刷新失败 → 清 token + 跳 /login + 抛出原错误', async () => {
    const err = fetchError(401, { message: 'unauthorized' })
    mocks.fetchMock.mockRejectedValue(err)
    mocks.refreshAccessTokenMock.mockResolvedValue(false)

    await expect(apiFetch('/admin/stats')).rejects.toBe(err)
    expect(mocks.clearTokensMock).toHaveBeenCalledTimes(1)
    expect(mocks.navigateMock).toHaveBeenCalledWith('/login')
  })

  it('401 重放后再次 401：登出跳登录，不再无限刷新', async () => {
    mocks.fetchMock
      .mockRejectedValueOnce(fetchError(401, {}))
      .mockRejectedValueOnce(fetchError(401, {}))
    mocks.refreshAccessTokenMock.mockResolvedValue(true)

    await expect(apiFetch('/admin/x')).rejects.toBeTruthy()
    expect(mocks.refreshAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(mocks.fetchMock).toHaveBeenCalledTimes(2)
    expect(mocks.clearTokensMock).toHaveBeenCalledTimes(1)
    expect(mocks.navigateMock).toHaveBeenCalledWith('/login')
  })

  it('503 + OOBE_REQUIRED：跳转 /oobe 且不 toast', async () => {
    const err = fetchError(503, { error_code: 'OOBE_REQUIRED' })
    mocks.fetchMock.mockRejectedValue(err)

    await expect(apiFetch('/blog/posts')).rejects.toBe(err)
    expect(mocks.navigateMock).toHaveBeenCalledWith('/oobe')
    expect(mocks.toastErrorMock).not.toHaveBeenCalled()
  })

  it('网络层错误（status 0）：toast 明确提示并抛 NETWORK_ERROR', async () => {
    mocks.fetchMock.mockRejectedValue(Object.assign(new Error('Failed to fetch'), { status: 0 }))

    await expect(apiFetch('/blog/posts')).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
      message: '无法连接到后端服务，请确认已启动后端或检查网络'
    })
    expect(mocks.toastErrorMock).toHaveBeenCalledWith('无法连接到后端服务，请确认已启动后端或检查网络')
  })

  it('超时中止（abort）给出可操作的重试提示', async () => {
    mocks.fetchMock.mockRejectedValue(
      Object.assign(new Error('The operation was aborted'), { status: 0 })
    )

    await expect(apiFetch('/media/upload', { method: 'POST' })).rejects.toMatchObject({
      message: '请求已取消（上传超时），请重试或上传更小的文件'
    })
  })

  it('404：必须 toast「接口不存在」而不是静默', async () => {
    mocks.fetchMock.mockRejectedValue(fetchError(404, {}))

    await expect(apiFetch('/admin/nope')).rejects.toMatchObject({ code: 'NOT_FOUND' })
    expect(mocks.toastErrorMock).toHaveBeenCalledWith('接口不存在 (404): /admin/nope')
  })

  it('413：文件过大提示', async () => {
    mocks.fetchMock.mockRejectedValue(fetchError(413, null))
    await expect(apiFetch('/media', { method: 'POST' })).rejects.toMatchObject({
      code: 'PAYLOAD_TOO_LARGE'
    })
    expect(mocks.toastErrorMock).toHaveBeenCalledWith('文件过大，超过服务器允许的上传大小')
  })

  it('一般失败：优先 toast 后端错误包络 message', async () => {
    mocks.fetchMock.mockRejectedValue(fetchError(500, { message: '数据库连接失败' }))
    await expect(apiFetch('/x')).rejects.toBeTruthy()
    expect(mocks.toastErrorMock).toHaveBeenCalledWith('数据库连接失败')
  })

  it('silentToast: true 时不 toast，但仍抛错', async () => {
    const err = fetchError(500, { message: 'boom' })
    mocks.fetchMock.mockRejectedValue(err)
    await expect(apiFetch('/x', { silentToast: true })).rejects.toBe(err)
    expect(mocks.toastErrorMock).not.toHaveBeenCalled()
  })
})

describe('useApi · silentApiFetch 静默降级契约', () => {
  it('默认同样享受 15s 超时；FormData 不套默认超时', async () => {
    mocks.fetchMock.mockResolvedValue({ n: 1 })
    await silentApiFetch('/notices/badge')
    expect(lastFetchOptions().timeout).toBe(15_000)

    const fd = new FormData()
    fd.append('f', 'v')
    await silentApiFetch('/upload', { method: 'POST', body: fd })
    expect(lastFetchOptions().timeout).toBeUndefined()
  })

  it('任意失败返回 null 且绝不 toast', async () => {
    mocks.fetchMock.mockRejectedValue(fetchError(500, { message: 'x' }))
    await expect(silentApiFetch('/notices')).resolves.toBeNull()
    expect(mocks.toastErrorMock).not.toHaveBeenCalled()
  })

  it('401：刷新成功后重放；重试仍失败则吞掉返回 null', async () => {
    mocks.fetchMock
      .mockRejectedValueOnce(fetchError(401, {}))
      .mockRejectedValueOnce(fetchError(500, {}))
    mocks.refreshAccessTokenMock.mockResolvedValue(true)

    await expect(silentApiFetch('/notices')).resolves.toBeNull()
    expect(mocks.fetchMock).toHaveBeenCalledTimes(2)
    expect(mocks.clearTokensMock).not.toHaveBeenCalled()
  })

  it('401 刷新失败：清 token 跳 /login 并返回 null', async () => {
    mocks.fetchMock.mockRejectedValue(fetchError(401, {}))
    mocks.refreshAccessTokenMock.mockResolvedValue(false)

    await expect(silentApiFetch('/notices')).resolves.toBeNull()
    expect(mocks.clearTokensMock).toHaveBeenCalledTimes(1)
    expect(mocks.navigateMock).toHaveBeenCalledWith('/login')
  })

  it('OOBE 503：跳转 /oobe 且不抛错', async () => {
    mocks.fetchMock.mockRejectedValue(fetchError(503, { error_code: 'OOBE_REQUIRED' }))
    await expect(silentApiFetch('/blog/posts')).resolves.toBeNull()
    expect(mocks.navigateMock).toHaveBeenCalledWith('/oobe')
  })
})

describe('useApi · useAPI（useFetch 包装）契约', () => {
  /** 在测试里直接调用 useAPI：所有 Nuxt 运行时已被 mock，无需真实 setup 上下文。 */
  function invokeUseAPI(url: string, options?: ApiUseFetchOptions<unknown>) {
    useAPI(url, options)
    return mocks.useFetchCaptured!
  }

  it('默认超时 15s、客户端 baseURL、稳定 key 与调用方 key 优先级', () => {
    const opts = invokeUseAPI('/blog/posts')
    expect(opts.timeout).toBe(15_000)
    expect(opts.baseURL).toBe('/api')
    expect(opts.key).toBe('api::/blog/posts')

    const opts2 = invokeUseAPI('/blog/posts', { key: 'custom-key' })
    expect(opts2.key).toBe('custom-key')
  })

  it('headers 为响应式：store token 注入 Bearer，且覆盖调用方手传 Authorization', () => {
    mocks.authState.accessToken = 'tok-1'
    const opts = invokeUseAPI('/blog/posts', { headers: { Authorization: 'Bearer fake' } })
    expect(opts.headers.value.Authorization).toBe('Bearer tok-1')
    expect(opts.headers.value['Accept-Language']).toBe('en')
  })

  it('onResponseError：503+OOBE_REQUIRED 跳 /oobe', async () => {
    const opts = invokeUseAPI('/blog/posts')
    await opts.onResponseError({ response: { status: 503, _data: { error_code: 'OOBE_REQUIRED' } } })
    expect(mocks.navigateMock).toHaveBeenCalledWith('/oobe')
  })

  it('onResponseError：401 刷新成功后不登出；重放后仍 401 才登出跳 /login', async () => {
    mocks.authState.refreshToken = 'r-1'
    mocks.refreshAccessTokenMock.mockResolvedValue(true)
    const opts = invokeUseAPI('/blog/posts')

    await opts.onResponseError({ response: { status: 401, _data: {} } })
    expect(mocks.refreshAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(mocks.clearTokensMock).not.toHaveBeenCalled()
    expect(mocks.navigateMock).not.toHaveBeenCalled()

    // 刷新成功后 headers 变化触发自动重发；重发仍 401 → 防死循环登出
    await opts.onResponseError({ response: { status: 401, _data: {} } })
    expect(mocks.refreshAccessTokenMock).toHaveBeenCalledTimes(1)
    expect(mocks.clearTokensMock).toHaveBeenCalledTimes(1)
    expect(mocks.navigateMock).toHaveBeenCalledWith('/login')
  })

  it('onResponse：成功响应复位防重放标记', async () => {
    mocks.authState.refreshToken = 'r-1'
    mocks.refreshAccessTokenMock.mockResolvedValue(true)
    const opts = invokeUseAPI('/blog/posts')

    await opts.onResponseError({ response: { status: 401, _data: {} } })
    opts.onResponse({})
    await opts.onResponseError({ response: { status: 401, _data: {} } })
    // 复位后第二次 401 应再次尝试刷新而不是直接登出
    expect(mocks.refreshAccessTokenMock).toHaveBeenCalledTimes(2)
    expect(mocks.clearTokensMock).not.toHaveBeenCalled()
  })

  it('onResponseError：401 且无 refreshToken → 直接登出跳转', async () => {
    const opts = invokeUseAPI('/blog/posts')
    await opts.onResponseError({ response: { status: 401, _data: {} } })
    expect(mocks.refreshAccessTokenMock).not.toHaveBeenCalled()
    expect(mocks.clearTokensMock).toHaveBeenCalledTimes(1)
    expect(mocks.navigateMock).toHaveBeenCalledWith('/login')
  })

  it('调用方自传的 onRequest/onResponse/onResponseError 不被内置钩子静默覆盖', async () => {
    const calls: string[] = []
    const opts = invokeUseAPI('/blog/posts', {
      onRequest: () => calls.push('request'),
      onResponse: () => calls.push('response'),
      onResponseError: () => { calls.push('error') }
    })
    await opts.onRequest({})
    await opts.onResponse({})
    await opts.onResponseError({ response: { status: 400, _data: {} } })
    expect(calls).toEqual(['request', 'response', 'error'])
  })
})
