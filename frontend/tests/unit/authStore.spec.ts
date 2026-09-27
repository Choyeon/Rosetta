import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const mocks = vi.hoisted(() => ({
  fetchMock: vi.fn(),
  nuxtApp: {
    payload: { serverRendered: true } as Record<string, unknown>,
    hook: vi.fn(),
    $i18n: { locale: { value: 'zh' } }
  }
}))

vi.mock('#app/nuxt', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return {
    ...actual,
    useRuntimeConfig: () => ({
      apiBase: 'http://127.0.0.1:8000/api',
      public: { apiBase: '/api' }
    }),
    useNuxtApp: () => mocks.nuxtApp
  }
})
vi.mock('#build/fetch.mjs', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return { ...actual, $fetch: mocks.fetchMock }
})

function httpError(status: number, data?: unknown) {
  return Object.assign(new Error(`http ${status}`), { status, data })
}

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
  localStorage.clear()
  delete (window as unknown as { __NUXT_HYDRATED__?: boolean }).__NUXT_HYDRATED__
  mocks.nuxtApp.payload = { serverRendered: true }
  mocks.fetchMock.mockResolvedValue({ id: 1, username: 'admin', role: 'admin' })
})

describe('stores/auth 认证状态契约', () => {
  it('setTokens / clearTokens 同步 localStorage 持久化', () => {
    const store = useAuthStore()
    store.setTokens({ access_token: 'a-tok', refresh_token: 'r-tok' } as never)
    expect(store.accessToken).toBe('a-tok')
    expect(localStorage.getItem('access_token')).toBe('a-tok')
    expect(localStorage.getItem('refresh_token')).toBe('r-tok')

    store.clearTokens()
    expect(store.accessToken).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('isAdmin 兼容 staff/superuser 布尔位与多种 role 字符串', () => {
    const store = useAuthStore()
    store.user = { id: 1, username: 'x', is_staff: true }
    expect(store.isAdmin).toBe(true)

    store.user = { id: 2, username: 'y', role: 'SUPERUSER' }
    expect(store.isAdmin).toBe(true)

    store.user = { id: 3, username: 'z', role: 'member' }
    expect(store.isAdmin).toBe(false)

    store.user = null
    expect(store.isAdmin).toBe(false)
  })

  describe('refreshAccessToken 刷新契约', () => {
    it('成功：写入新 token 对并返回 true', async () => {
      const store = useAuthStore()
      store.refreshToken = 'old-r'
      mocks.fetchMock.mockResolvedValue({ access_token: 'new-a', refresh_token: 'new-r' })

      await expect(store.refreshAccessToken()).resolves.toBe(true)
      expect(store.accessToken).toBe('new-a')
      expect(mocks.fetchMock).toHaveBeenCalledWith('/users/refresh', expect.objectContaining({
        baseURL: '/api', method: 'POST'
      }))
    })

    it('失败：清登录态返回 false', async () => {
      const store = useAuthStore()
      store.refreshToken = 'old-r'
      mocks.fetchMock.mockRejectedValue(httpError(401, {}))

      await expect(store.refreshAccessToken()).resolves.toBe(false)
      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
    })

    it('无 refreshToken：不请求后端直接 false', async () => {
      const store = useAuthStore()
      await expect(store.refreshAccessToken()).resolves.toBe(false)
      expect(mocks.fetchMock).not.toHaveBeenCalled()
    })

    it('并发 401 互斥：多个同时刷新只发一次 /users/refresh（rotate 语义防 TOKEN_REUSED）', async () => {
      const store = useAuthStore()
      store.refreshToken = 'r'
      let release: (v: unknown) => void = () => {}
      mocks.fetchMock.mockImplementation(() => {
        return new Promise((resolve) => {
          release = resolve
        })
      })

      const p1 = store.refreshAccessToken()
      const p2 = store.refreshAccessToken()
      release({ access_token: 'a2', refresh_token: 'r2' })
      await expect(Promise.all([p1, p2])).resolves.toEqual([true, true])
      expect(mocks.fetchMock).toHaveBeenCalledTimes(1)
    })
  })

  describe('initialize() hydration 时序契约', () => {
    it('ssr:false 空壳页（payload.serverRendered=false）：立即恢复 token，不等 app:mounted', async () => {
      localStorage.setItem('access_token', 'shell-a')
      localStorage.setItem('refresh_token', 'shell-r')
      mocks.nuxtApp.payload = { serverRendered: false }
      const store = useAuthStore()

      await store.initialize()

      expect(store.accessToken).toBe('shell-a')
      expect(store.refreshToken).toBe('shell-r')
      expect(mocks.nuxtApp.hook).not.toHaveBeenCalled()
      expect(mocks.fetchMock).toHaveBeenCalledWith('/users/me', expect.objectContaining({
        baseURL: '/api',
        headers: { Authorization: 'Bearer shell-a' }
      }))
    })

    it('SSR 页：hydrate 完成前绝不写状态，app:mounted 后才恢复', async () => {
      localStorage.setItem('access_token', 'ssr-a')
      localStorage.setItem('refresh_token', 'ssr-r')
      const store = useAuthStore()

      let mountedCb: (() => void) | undefined
      mocks.nuxtApp.hook.mockImplementation((_name: string, cb: () => void) => {
        mountedCb = cb
      })

      let settled = false
      const p = store.initialize().then(() => {
        settled = true
      })
      await vi.waitFor(() => expect(mocks.nuxtApp.hook).toHaveBeenCalledWith('app:mounted', expect.any(Function)))

      // 放行点未触发前：promise 挂起、token 未写入（避免 Hydration mismatch）
      expect(settled).toBe(false)
      expect(store.accessToken).toBeNull()

      mountedCb!()
      await p
      expect(store.accessToken).toBe('ssr-a')
      expect(store.isAuthenticated).toBe(true)
    })

    it('完成后打 __NUXT_HYDRATED__ 标记且 initialize 幂等（重复调用不再拉取用户）', async () => {
      localStorage.setItem('access_token', 'a')
      localStorage.setItem('refresh_token', 'r')
      mocks.nuxtApp.payload = { serverRendered: false }
      const store = useAuthStore()

      await store.initialize()
      await store.initialize()
      expect(mocks.fetchMock.mock.calls.filter(c => c[0] === '/users/me')).toHaveLength(1)
      expect((window as unknown as { __NUXT_HYDRATED__?: boolean }).__NUXT_HYDRATED__).toBe(true)
    })

    it('localStorage 无 token：初始化后保持未登录', async () => {
      mocks.nuxtApp.payload = { serverRendered: false }
      const store = useAuthStore()
      await store.initialize()
      expect(store.isAuthenticated).toBe(false)
      expect(mocks.fetchMock).not.toHaveBeenCalled()
    })

    it('fetchUser 收到 401 → 清空登录态', async () => {
      const store = useAuthStore()
      store.accessToken = 'expired'
      mocks.fetchMock.mockRejectedValue(httpError(401, {}))

      await store.fetchUser()
      expect(store.accessToken).toBeNull()
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })

  describe('login / logout 错误与清理契约', () => {
    it('登录成功写入 token 并拉取用户资料', async () => {
      mocks.fetchMock
        .mockResolvedValueOnce({ access_token: 'la', refresh_token: 'lr' })
        .mockResolvedValueOnce({ id: 9, username: 'admin' })
      const store = useAuthStore()

      await store.login('admin', 'pass')
      expect(store.accessToken).toBe('la')
      expect(store.user?.username).toBe('admin')
    })

    it('登录失败：错误 message > detail > errors[0].message > 兜底文案', async () => {
      const store = useAuthStore()

      mocks.fetchMock.mockRejectedValue(httpError(401, { message: '账号或密码错误' }))
      await expect(store.login('a', 'b')).rejects.toThrow('账号或密码错误')

      mocks.fetchMock.mockRejectedValue(httpError(422, { detail: '字段校验失败' }))
      await expect(store.login('a', 'b')).rejects.toThrow('字段校验失败')

      mocks.fetchMock.mockRejectedValue(httpError(400, { errors: [{ field: 'password', message: '密码至少 8 位' }] }))
      await expect(store.login('a', 'b')).rejects.toThrow('密码至少 8 位')

      mocks.fetchMock.mockRejectedValue(httpError(500, {}))
      await expect(store.login('a', 'b')).rejects.toThrow('登录失败，请稍后再试')
    })

    it('登录被锁 423：外泄 retryAfterSeconds + errorCode，供登录页展示倒计时', async () => {
      const store = useAuthStore()
      mocks.fetchMock.mockRejectedValue(
        httpError(423, { error_code: 'ACCOUNT_LOCKED', message: '账号因多次登录失败已被暂时锁定', retry_after_seconds: 120 })
      )

      await expect(store.login('a', 'b')).rejects.toMatchObject({
        message: '账号因多次登录失败已被暂时锁定',
        errorCode: 'ACCOUNT_LOCKED',
        status: 423,
        retryAfterSeconds: 120
      })
    })

    it('非锁定错误不带 retryAfterSeconds（不误触发倒计时）', async () => {
      const store = useAuthStore()
      mocks.fetchMock.mockRejectedValue(httpError(401, { error_code: 'AUTH_INVALID_CREDENTIALS', message: '密码错误' }))

      const err = (await store.login('a', 'b').catch((e: unknown) => e)) as { retryAfterSeconds?: number }
      expect(err.retryAfterSeconds).toBe(0)
    })

    it('登出：后端调用失败也必须本地清态（finally 兜底）', async () => {
      const store = useAuthStore()
      store.setTokens({ access_token: 'a', refresh_token: 'r' } as never)
      mocks.fetchMock.mockRejectedValue(httpError(500, {}))

      await store.logout()
      expect(store.accessToken).toBeNull()
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })

  describe('register 错误契约', () => {
    it('读统一失败信封 message（旧实现只看 detail，会把业务错误吞成兜底文案）', async () => {
      const store = useAuthStore()
      mocks.fetchMock.mockRejectedValue(httpError(400, { error_code: 'WEAK_PASSWORD', message: '密码强度不足' }))

      const err = (await store.register('u', 'e@x.com', '123').catch((e: unknown) => e)) as { message: string, errorCode?: string }
      expect(err.message).toBe('密码强度不足')
      expect(err.errorCode).toBe('WEAK_PASSWORD')
    })

    it('校验错误走 errors[0].message', async () => {
      const store = useAuthStore()
      mocks.fetchMock.mockRejectedValue(httpError(400, { errors: [{ field: 'email', message: '邮箱已存在' }] }))

      await expect(store.register('u', 'e@x.com', 'pass1234')).rejects.toThrow('邮箱已存在')
    })

    it('信封全空才落兜底文案', async () => {
      const store = useAuthStore()
      mocks.fetchMock.mockRejectedValue(httpError(500, {}))

      await expect(store.register('u', 'e@x.com', 'pass1234')).rejects.toThrow('Registration failed')
    })
  })
})
