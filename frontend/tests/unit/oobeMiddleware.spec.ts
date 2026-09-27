import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { RouteMiddleware } from '#app'

/** 中间件探测 /oobe/status 时真实传给 $fetch 的选项形状。 */
interface ProbeOptions {
  baseURL?: string
  timeout?: number
  signal?: AbortSignal
  [k: string]: unknown
}

type FetchMockFn = (url: string, opts: ProbeOptions) => Promise<unknown>

const mocks = vi.hoisted(() => ({
  fetchMock: vi.fn<FetchMockFn>(),
  navigateMock: vi.fn(async (..._args: unknown[]) => undefined),
  // SSR 水合进 payload 的 oobe:status 值（useState 的返回源），按测试用例改写
  hydratedState: undefined as boolean | null | undefined,
  stateCalls: 0
}))

vi.mock('#app/nuxt', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return {
    ...actual,
    useRuntimeConfig: () => ({
      apiBase: 'http://127.0.0.1:8000/api',
      public: { apiBase: '/api' }
    })
  }
})
vi.mock('#build/fetch.mjs', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return { ...actual, $fetch: mocks.fetchMock }
})
vi.mock('#app/composables/router', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return {
    ...actual,
    // 中间件注册器在单测里退化为恒等函数，直接拿到回调本体
    defineNuxtRouteMiddleware: (fn: unknown) => fn,
    navigateTo: mocks.navigateMock
  }
})
vi.mock('#app/composables/state', () => ({
  useState: (_key: string, init?: () => boolean | null | undefined) => {
    mocks.stateCalls++
    return {
      get value() {
        return mocks.hydratedState === undefined ? (init ? init() : undefined) : mocks.hydratedState
      },
      set value(v: boolean | null | undefined) {
        mocks.hydratedState = v
      }
    }
  }
}))

type MiddlewareModule = {
  default: RouteMiddleware
  resetOOBECache: (nextValue?: boolean | null) => void
}

/** 每次重新加载模块，隔离模块级 60s 缓存 / clientResolved / inFlight 状态。 */
async function loadOOBEMiddleware(): Promise<MiddlewareModule> {
  vi.resetModules()
  return await import('@/middleware/oobe.global') as unknown as MiddlewareModule
}

async function runMiddleware(mw: RouteMiddleware, path: string) {
  return await mw({ path } as never, { path } as never)
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.hydratedState = undefined
  mocks.stateCalls = 0
  mocks.fetchMock.mockResolvedValue({ success: true, oobe_complete: true })
  // 清理上一次导航遗留的 window 级重路由锁
  delete (globalThis as Record<string, unknown>).__ros_oobe_reroute_lock__
  delete (globalThis as Record<string, unknown>).__ros_oobe_reroute_done__
})

describe('oobe.global 中间件导航守卫契约', () => {
  it('静态资源与 API 路径直接跳过探测（不打后端、不重定向）', async () => {
    const { default: mw } = await loadOOBEMiddleware()
    for (const path of ['/favicon.ico', '/api/blog/rss', '/_nuxt/entry.js', '/images/cover.png', '/logo.svg']) {
      await runMiddleware(mw, path)
    }
    expect(mocks.fetchMock).not.toHaveBeenCalled()
    expect(mocks.navigateMock).not.toHaveBeenCalled()
  })

  it('探测走 /oobe/status 且带 8s 超时（不占用无上限请求槽）', async () => {
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/')
    expect(mocks.fetchMock).toHaveBeenCalledTimes(1)
    const probeCall = mocks.fetchMock.mock.calls[0]
    if (!probeCall) throw new Error('中间件未发起 /oobe/status 探测请求')
    const [url, opts] = probeCall
    expect(url).toBe('/oobe/status')
    expect(opts.baseURL).toBe('/api')
    expect(opts.timeout).toBe(8_000)
  })

  it('已安装 + 访问 /oobe → replace 回首页', async () => {
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/oobe')
    expect(mocks.navigateMock).toHaveBeenCalledWith('/', { replace: true, external: false })
  })

  it('未安装 + 访问普通页 → replace 去 /oobe', async () => {
    mocks.fetchMock.mockResolvedValue({ oobe_complete: false })
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/posts/hello')
    expect(mocks.navigateMock).toHaveBeenCalledWith('/oobe', { replace: true })
  })

  it('未安装 + 已在 /oobe：不再重定向（向导页可停留）', async () => {
    mocks.fetchMock.mockResolvedValue({ oobe_complete: false })
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/oobe')
    expect(mocks.navigateMock).not.toHaveBeenCalled()
  })

  it('后端不可达 = 状态未知：一律放行当前路由，绝不重定向', async () => {
    mocks.fetchMock.mockRejectedValue(Object.assign(new Error('connect ECONNREFUSED'), { status: 0 }))
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/posts/hello')
    expect(mocks.navigateMock).not.toHaveBeenCalled()
  })

  it('未知态 30s sticky：连续导航不重复打后端，也持续放行', async () => {
    mocks.fetchMock.mockRejectedValue(Object.assign(new Error('boom'), { status: 500 }))
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/')
    await runMiddleware(mw, '/posts')
    expect(mocks.fetchMock).toHaveBeenCalledTimes(1)
    expect(mocks.navigateMock).not.toHaveBeenCalled()
  })

  it('429 不得被误判为「已安装」（安装期限流不能挡死向导入口）', async () => {
    mocks.fetchMock.mockRejectedValue(Object.assign(new Error('too many'), { status: 429 }))
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/oobe')
    // 未知态：停在 /oobe，不弹回首页
    expect(mocks.navigateMock).not.toHaveBeenCalled()
  })

  it('客户端 60s 缓存：成功判定后跨导航复用，不再请求', async () => {
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/')
    await runMiddleware(mw, '/about')
    await runMiddleware(mw, '/oobe')
    expect(mocks.fetchMock).toHaveBeenCalledTimes(1)
    // 第三次导航命中缓存 true，仍在 /oobe 被送回首页
    expect(mocks.navigateMock).toHaveBeenCalledTimes(1)
    expect(mocks.navigateMock).toHaveBeenCalledWith('/', { replace: true, external: false })
  })

  it('并发导航合并 in-flight：只发一次状态请求', async () => {
    let release: (v: unknown) => void = () => {}
    mocks.fetchMock.mockImplementation(() => {
      return new Promise((resolve) => {
        release = resolve
      })
    })
    const { default: mw } = await loadOOBEMiddleware()

    const p1 = runMiddleware(mw, '/')
    const p2 = runMiddleware(mw, '/about')
    release({ oobe_complete: true })
    await Promise.all([p1, p2])
    expect(mocks.fetchMock).toHaveBeenCalledTimes(1)
  })

  it('首屏消费 SSR 水合值：payload 里已有判定时不再重复请求', async () => {
    // 模拟 SSR 已判「未安装」并随 payload 水合（useState 读取到 boolean）
    mocks.hydratedState = false
    const { default: mw } = await loadOOBEMiddleware()
    await runMiddleware(mw, '/posts')
    expect(mocks.fetchMock, 'SSR 水合值应被首屏一次性消费，禁止重复探测').not.toHaveBeenCalled()
    expect(mocks.navigateMock).toHaveBeenCalledWith('/oobe', { replace: true })
  })

  it('resetOOBECache(true)：安装完成后即时翻转，/oobe 立即回首页且零请求', async () => {
    const { default: mw, resetOOBECache } = await loadOOBEMiddleware()
    resetOOBECache(true)
    await runMiddleware(mw, '/oobe')
    expect(mocks.fetchMock).not.toHaveBeenCalled()
    expect(mocks.navigateMock).toHaveBeenCalledWith('/', { replace: true, external: false })
  })

  it('resetOOBECache(false)：重装/回滚场景即时生效，普通页被拦进向导', async () => {
    const { default: mw, resetOOBECache } = await loadOOBEMiddleware()
    resetOOBECache(false)
    await runMiddleware(mw, '/')
    expect(mocks.fetchMock).not.toHaveBeenCalled()
    expect(mocks.navigateMock).toHaveBeenCalledWith('/oobe', { replace: true })
  })
})
