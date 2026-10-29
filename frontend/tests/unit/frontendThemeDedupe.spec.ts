/**
 * GET /api/themes/active 的首屏去重回归钉（2026-10-29）。
 *
 * 现场：线上首页一次加载稳定发出 **3 条** GET /api/themes/active（性能面板实测，起始时间
 * 656 / 708 / 747 ms；plugin 01-site-bootstrap、layouts/default、pages/index 三处
 * 在 app:mounted 各排了一次纠偏）。根因不是"排了三次"——那三处调用本来就该被
 * in-flight 去重吸收——而是**去重表的键选错了**：
 *
 *   Nuxt 的 useState 实现是 `toRef(nuxtApp.payload.state, key)`，每次调用都新建一个
 *   ObjectRefImpl 包装。以这个 ref 为键的 WeakMap/WeakSet 只在**同一个** composable
 *   实例内命中，跨实例永远不相等 → 每个调用方各拿自己那把钥匙，去重与"已拉过一次"
 *   的闩锁同时失效。这也是 AppFooter / AppHeader / 各页面都能在 SPA 导航时各再请求一次的原因。
 *
 * 口径：两张表都以 NuxtApp 为键（SSR 下每个请求一个 app，跨请求仍隔离）。
 * 本测试按 Nuxt 的真实语义桩出 useState：**共享同一份 payload 对象、每次调用返回新的 ref 包装**，
 * 因此"两个实例并发 ensureLoaded 只发一条请求"在旧实现下必红。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { toRef } from 'vue'

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  app: {
    hooks: { hook: vi.fn() },
    payload: { state: {} } as Record<string, unknown>
  }
}))

vi.mock('~~/composables/useApi', () => ({
  apiFetch: mocks.apiFetch,
  useAPI: vi.fn(),
  silentApiFetch: vi.fn()
}))

vi.mock('#app/nuxt', () => ({ useNuxtApp: () => mocks.app }))
vi.mock('#app/composables/router', () => ({
  useRoute: () => ({ path: '/', query: {} })
}))

// 关键：复刻 Nuxt 的 useState —— 共享 payload.state，但每次返回新的 ObjectRefImpl。
vi.mock('#app/composables/state', () => ({
  useState: (key: string, init?: () => unknown) => {
    const bag = (mocks.app.payload as { state: Record<string, unknown> }).state
    const state = toRef(bag, key)
    if (state.value === undefined && typeof init === 'function') state.value = init()
    return state
  },
  clearNuxtState: vi.fn()
}))

const { useFrontendTheme } = await import('@/composables/useFrontendTheme')
const { useSite } = await import('@/composables/useSite')

const activePayload = {
  success: true,
  data: {
    slug: 'editorial-wp-style',
    name: '默认主题',
    version: '1.1.3',
    screenshot_urls: [],
    mods: {},
    mods_schema: null
  }
}

describe('useFrontendTheme 的 /themes/active 全 app 去重', () => {
  beforeEach(() => {
    // 去重表以 NuxtApp 为键，每个用例换一个 app 实例才会拿到干净的去重/闩锁状态
    mocks.app = { hooks: { hook: vi.fn() }, payload: { state: {} } }
    mocks.apiFetch.mockReset()
    mocks.apiFetch.mockResolvedValue(activePayload)
  })

  it('多个 composable 实例并发 ensureLoaded 只发一条请求（旧实现：每实例一条）', async () => {
    // 三个调用方 = plugin 01-site-bootstrap / layouts/default / pages/index 的真实形状
    const a = useFrontendTheme()
    const b = useFrontendTheme()
    const c = useFrontendTheme()

    await Promise.all([a.ensureLoaded(), b.ensureLoaded(), c.ensureLoaded()])

    expect(mocks.apiFetch).toHaveBeenCalledTimes(1)
    expect(mocks.apiFetch.mock.calls[0]?.[0]).toBe('/themes/active')
    // 请求体写回的是共享 payload：任一实例都能读到同一份主题信息
    expect(a.state.value.slug).toBe('editorial-wp-style')
    expect(c.state.value.version).toBe('1.1.3')
  })

  it('已完成一次真实验证后，新实例的 ensureLoaded 直接命中闩锁（不再请求）', async () => {
    await useFrontendTheme().ensureLoaded()
    expect(mocks.apiFetch).toHaveBeenCalledTimes(1)

    await useFrontendTheme().ensureLoaded()
    expect(mocks.apiFetch).toHaveBeenCalledTimes(1)
  })

  it('reload()/force 仍然能真正重拉（去重不等于永久缓存）', async () => {
    await useFrontendTheme().ensureLoaded()
    await useFrontendTheme().reload()
    expect(mocks.apiFetch).toHaveBeenCalledTimes(2)
  })
})

describe('useSite 的 /config + /settings/public 同口径去重', () => {
  beforeEach(() => {
    mocks.app = { hooks: { hook: vi.fn() }, payload: { state: {} } }
    mocks.apiFetch.mockReset()
    mocks.apiFetch.mockImplementation(async (url: string) => {
      if (url === '/config') return { site_name: 'Choyeon Blog' }
      if (url === '/settings/public') return { groups: { basic: { site_name: 'Choyeon Blog' } } }
      return activePayload
    })
  })

  it('多个实例并发 ensureLoaded：config / settings / theme 各只拉一次', async () => {
    const a = useSite()
    const b = useSite()

    await Promise.all([a.ensureLoaded(), b.ensureLoaded()])

    const urls = mocks.apiFetch.mock.calls.map(c => c[0])
    expect(urls.filter(u => u === '/config')).toHaveLength(1)
    expect(urls.filter(u => u === '/settings/public')).toHaveLength(1)
    expect(urls.filter(u => u === '/themes/active')).toHaveLength(1)
    expect(a.state.value.loaded).toBe(true)
  })

  it('已完成加载后新实例直接返回（force 才重拉）', async () => {
    await useSite().ensureLoaded()
    const callsAfterFirst = mocks.apiFetch.mock.calls.length

    await useSite().ensureLoaded()
    expect(mocks.apiFetch.mock.calls.length).toBe(callsAfterFirst)

    await useSite().ensureLoaded({ force: true })
    expect(mocks.apiFetch.mock.calls.length).toBeGreaterThan(callsAfterFirst)
  })
})
