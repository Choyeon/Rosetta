/**
 * 后台管理通用 CRUD 助手。
 * 封装列表加载、分页、搜索、选中态、增/改/删的通用流程与 toast 反馈，
 * 让各管理页聚焦业务字段而非重复样板。
 *
 * 设计要点：
 * - 所有请求走 apiFetch（自动注入 token / 语言 / 统一错误 toast），
 *   因此本助手不重复弹错，只负责成功 toast 与数据刷新。
 * - 列表函数由调用方提供（不同端点的查询参数不同），保持灵活。
 */
import { ref, reactive } from 'vue'
import { useToast } from '~~/composables/useToast'

export interface UseAdminCrudOptions<T, TCreate = Partial<T>, TUpdate = Partial<T>> {
  /** 加载列表，返回 { items, total } */
  fetchList: (params: {
    page: number
    pageSize: number
    search?: string
    [key: string]: unknown
  }) => Promise<{ items: T[], total: number }>
  /** 创建（可选，无则不支持新建） */
  create?: (payload: TCreate) => Promise<unknown>
  /** 更新（可选） */
  update?: (id: string | number, payload: TUpdate) => Promise<unknown>
  /** 删除单个（可选） */
  remove?: (id: string | number) => Promise<unknown>
  /** 批量删除（可选） */
  removeBatch?: (ids: Array<string | number>) => Promise<unknown>
  /** 实体 id 字段名 */
  idKey?: keyof T
  /** 成功提示文案 */
  labels?: {
    create?: string
    update?: string
    remove?: string
    removeBatch?: string
    loadError?: string
  }
  /** 额外固定查询参数（如 status / category） */
  extraParams?: Record<string, unknown>
}

export function useAdminCrud<T, TCreate = Partial<T>, TUpdate = Partial<T>>(
  options: UseAdminCrudOptions<T, TCreate, TUpdate>
) {
  const toast = useToast()
  const idKey = (options.idKey ?? 'id') as keyof T

  const items = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const loading = ref(false)
  const page = ref(1)
  const pageSize = ref(10)
  const search = ref('')
  const selectedIds = ref<Array<string | number>>([])
  const saving = ref(false)

  const labels = reactive({
    create: '创建成功',
    update: '保存成功',
    remove: '删除成功',
    removeBatch: '批量删除成功',
    loadError: '数据加载失败',
    ...options.labels
  })

  function getId(row: T): string | number {
    return row[idKey] as unknown as string | number
  }

  async function load() {
    loading.value = true
    try {
      const res = await options.fetchList({
        page: page.value,
        pageSize: pageSize.value,
        search: search.value.trim() || undefined,
        ...options.extraParams
      })
      items.value = res.items ?? []
      total.value = res.total ?? 0
    } catch {
      toast.error(labels.loadError)
    } finally {
      loading.value = false
    }
  }

  function onPageChange(p: number) {
    page.value = p
    load()
  }

  function onPageSizeChange(size: number) {
    pageSize.value = size
    page.value = 1
    load()
  }

  function onSearch() {
    page.value = 1
    load()
  }

  function resetSearch() {
    search.value = ''
    page.value = 1
    load()
  }

  async function create(payload: TCreate) {
    if (!options.create) return
    saving.value = true
    try {
      await options.create(payload)
      toast.success(labels.create)
      await load()
    } catch {
      /* apiFetch 已统一 toast */
    } finally {
      saving.value = false
    }
  }

  async function update(id: string | number, payload: TUpdate) {
    if (!options.update) return
    saving.value = true
    try {
      await options.update(id, payload)
      toast.success(labels.update)
      await load()
    } catch {
      /* apiFetch 已统一 toast */
    } finally {
      saving.value = false
    }
  }

  async function remove(id: string | number) {
    if (!options.remove) return
    try {
      await options.remove(id)
      toast.success(labels.remove)
      selectedIds.value = selectedIds.value.filter(x => x !== id)
      await load()
    } catch {
      /* apiFetch 已统一 toast */
    }
  }

  async function removeBatch(ids: Array<string | number>) {
    if (!options.removeBatch || ids.length === 0) return
    try {
      await options.removeBatch(ids)
      toast.success(labels.removeBatch)
      selectedIds.value = []
      await load()
    } catch {
      /* apiFetch 已统一 toast */
    }
  }

  return {
    items,
    total,
    loading,
    page,
    pageSize,
    search,
    selectedIds,
    saving,
    load,
    onPageChange,
    onPageSizeChange,
    onSearch,
    resetSearch,
    create,
    update,
    remove,
    removeBatch,
    getId
  }
}
