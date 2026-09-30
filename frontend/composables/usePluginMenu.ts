/**
 * 插件后台菜单（Sidebar「插件」分组）数据拉取。
 *
 * 数据来源：GET /api/admin/plugins/menu-registry
 *
 * 设计要点：
 * 1. 管理后台需要登录态，因此强制 server:false（纯客户端拉取），
 *    避免 SSR 端无 token 渲染为 401/加载错误。
 * 2. 失败静默降级（silentToast=true）：插件菜单是「锦上添花」的功能，
 *    即便拉取失败也不影响现有 admin 其它菜单。
 * 3. 在客户端页面切换之间缓存一份内存副本（reactive shallowRef），
 *    避免每次路由跳转都重拉。
 */

export interface PluginMenuItem {
  slug: string
  label: string
  icon: string
  path: string
  admin_route_prefix: string
  badge?: string | number
  extras?: Record<string, unknown>
}

export interface PluginMenuRegistryResponse {
  success: boolean
  data: {
    items: PluginMenuItem[]
    total: number
  }
  message?: string
}

// 进程级单例缓存（避免 Sidebar / AppHeader 各拉一次）。
// items/total 是模块级共享 ref：Sidebar 与管理页各自 usePluginMenu() 拿到的是同一份
// 响应式状态，管理页启用/停用插件后 load(true) 才能立刻刷新 Sidebar；
// 若每个调用方持有私有副本，缓存失效后旧副本会一直挂在菜单上。
// 约束：本 composable 只能在 /admin/**（routeRules 里 ssr:false）内调用。
// 模块级 ref 在 Nitro 进程内跨请求共享，一旦哪天有 SSR 页面引入它，
// 就会把 A 用户的菜单串给 B 用户——那时必须改成 useState。
const _items = ref<PluginMenuItem[]>([])
const _total = ref(0)
const _cache = {
  loaded: false,
  loadingPromise: null as Promise<PluginMenuItem[]> | null
}

export function usePluginMenu() {
  const items = _items
  const total = _total
  const loading = ref(false)
  const error = ref<unknown>(null)

  async function load(force = false): Promise<PluginMenuItem[]> {
    if (_cache.loaded && !force) {
      return _items.value
    }
    // force=true 时**不能**复用进行中的旧 Promise：那次请求是在插件启停之前发出的，
    // 复用它等于用陈旧结果冒充"刚强制刷新过"，侧栏会漏掉 / 残留刚刚变更的管理员菜单。
    // 正确做法是等旧请求落定再发一次新的 —— 慢一点没关系，语义不能错。
    // 非 force 的调用才允许共享同一个 in-flight Promise（避免并发重复请求）。
    if (_cache.loadingPromise) {
      if (!force) return _cache.loadingPromise
      try {
        await _cache.loadingPromise
      } catch {
        /* 旧请求失败不影响本次强制刷新 */
      }
    }
    loading.value = true
    error.value = null

    const task = (async () => {
      try {
        // 延迟导入 useApi，避免 setup 之外调用时 useRuntimeConfig 报错
        // （调用本 composable 的组件都会处于 setup 内，这里安全）
        const { apiFetch } = await import('~~/composables/useApi')

        const resp = await apiFetch<PluginMenuRegistryResponse>(
          '/admin/plugins/menu-registry',
          {
            method: 'GET',
            server: false,
            // 菜单加载失败不弹 toast（调用方也可以自行再提示）
            silentToast: true
          }
        )
        const list = Array.isArray(resp?.data?.items) ? resp.data.items : []
        _cache.loaded = true
        _items.value = list
        _total.value = resp?.data?.total ?? list.length
        return list
      } catch (e) {
        error.value = e
        // 即便失败也把 items 设为空数组（但缓存标记仍为 false，下次再尝试）
        _cache.loaded = false
        _items.value = []
        _total.value = 0
        return []
      } finally {
        loading.value = false
        _cache.loadingPromise = null
      }
    })()

    _cache.loadingPromise = task
    return task
  }

  function reset() {
    _cache.loaded = false
    _items.value = []
    _total.value = 0
    error.value = null
  }

  return {
    items,
    loading,
    error,
    total,
    load,
    reset
  }
}

/** Sidebar 用：生成与 config/admin-menu 同形状的 group（便于用同一组 UI）。 */
export function usePluginMenuGroup() {
  const { items, load, loading } = usePluginMenu()

  const group = computed(() => ({
    key: 'plugins',
    label: '插件',
    // 保留与其它分组结构一致：icon 由 items 承担
    items: items.value.map(it => ({
      path: it.path,
      label: it.label,
      iconName: it.icon,
      slug: it.slug,
      badge: it.badge
    }))
  }))

  return { group, items, load, loading }
}
