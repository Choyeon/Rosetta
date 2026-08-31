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

// 进程级单例缓存（避免 Sidebar / AppHeader 各拉一次）
const _cache = {
  loaded: false,
  items: [] as PluginMenuItem[],
  total: 0,
  loadingPromise: null as Promise<PluginMenuItem[]> | null
}

export function usePluginMenu() {
  const items = ref<PluginMenuItem[]>(_cache.items)
  const loading = ref(false)
  const error = ref<unknown>(null)
  const total = ref(_cache.total)

  async function load(force = false): Promise<PluginMenuItem[]> {
    if (_cache.loaded && !force && _cache.items.length) {
      items.value = _cache.items
      total.value = _cache.total
      return _cache.items
    }
    if (_cache.loadingPromise) {
      return _cache.loadingPromise
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
        _cache.items = list
        _cache.total = resp?.data?.total ?? list.length
        _cache.loaded = true
        items.value = _cache.items
        total.value = _cache.total
        return list
      } catch (e) {
        error.value = e
        // 即便失败也把 items 设为空数组（但缓存标记仍为 false，下次再尝试）
        _cache.items = []
        items.value = []
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
    _cache.items = []
    _cache.total = 0
    items.value = []
    total.value = 0
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
