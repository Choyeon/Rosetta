/**
 * 层级分类的树形取值单源（`Category.parent_id`）。
 *
 * 两个渲染面共用同一份算术：后台分类列表要按"父在前、子缩进"排序并在父级候选里
 * 排除自己的后代（否则选中就是一条 400），前台分类页要显祖先面包屑与子分类入口。
 *
 * 三条不变量（都是这里存在的原因）：
 * 1. **一条都不能从结果里消失**。悬空 `parent_id`（父级已删）、自指、库里躺着的环，
 *    都必须按顶级行落在列表末尾——后台少一行就等于那条分类再也改不动了。
 * 2. **不得死循环**。`parent_id` 只有外键、没有检查约束，环是能写进库的，
 *    所以每次上溯/下钻都带 visited 集合。
 * 3. **比较一律走字符串键**。`id` 在接口与类型里是 `number | string` 两形
 *    （SQLite 回吐整数、部分投影经 JSON 后是字符串），混着比会静默不匹配。
 */

export interface CategoryTreeRow {
  id: number | string
  /** 后端旧缓存可能整键缺失，所以是可选 */
  parent_id?: number | string | null
}

const rowKey = (value: unknown): string => (value == null ? '' : String(value))

function childrenMap(items: readonly CategoryTreeRow[]): Map<string, CategoryTreeRow[]> {
  const byId = new Set<string>()
  for (const item of items) {
    const k = rowKey(item.id)
    if (k) byId.add(k)
  }
  const children = new Map<string, CategoryTreeRow[]>()
  for (const item of items) {
    const p = rowKey(item.parent_id)
    // 悬空父级与自指不挂到任何父下（父级不存在时它自己就是列表里的一条顶级行）
    if (!p || p === rowKey(item.id) || !byId.has(p)) continue
    const bucket = children.get(p)
    if (bucket) bucket.push(item)
    else children.set(p, [item])
  }
  return children
}

export interface CategoryTreeEntry<T extends CategoryTreeRow> {
  item: T
  depth: number
}

/**
 * 展开成"深度优先 + 缩进层级"的线性列表：顶级在前，其子分类紧随，孙级再缩一档。
 * 输入顺序即同层兄弟顺序（后端按 `created_at` 返回，后台列表不再重排）。
 */
export function buildCategoryTree<T extends CategoryTreeRow>(
  items: readonly T[]
): Array<CategoryTreeEntry<T>> {
  const byId = new Map<string, T>()
  for (const item of items) {
    const k = rowKey(item.id)
    if (k && !byId.has(k)) byId.set(k, item)
  }
  const children = childrenMap(items)
  const out: Array<CategoryTreeEntry<T>> = []
  const visited = new Set<string>()

  const walk = (row: T, depth: number) => {
    const k = rowKey(row.id)
    if (!k || visited.has(k)) return
    visited.add(k)
    out.push({ item: row, depth })
    for (const child of children.get(k) ?? []) {
      // 类型在这里收窄回 T：children 桶里的行与 items 同源
      walk(child as T, depth + 1)
    }
  }

  for (const item of items) {
    const p = rowKey(item.parent_id)
    if (!p || p === rowKey(item.id) || !byId.has(p)) walk(item, 0)
  }
  // 环上的分类从任何顶级都不可达：补一趟，保证后台列表一条不少
  for (const item of items) walk(item, 0)

  return out
}

/** 某行的全部后代 id（不含自身）。后台父级候选据此排除"选了就是环"的项。 */
export function categoryDescendantIds(
  items: readonly CategoryTreeRow[],
  id: number | string | null | undefined
): Set<string> {
  const start = rowKey(id)
  const found = new Set<string>()
  if (!start) return found
  const children = childrenMap(items)
  const queue: CategoryTreeRow[] = [...(children.get(start) ?? [])]
  while (queue.length > 0) {
    const row = queue.shift()
    if (!row) continue
    const k = rowKey(row.id)
    if (!k || found.has(k)) continue
    found.add(k)
    for (const child of children.get(k) ?? []) queue.push(child)
  }
  return found
}

/**
 * 某行的祖先链，**由远及近**（根在前），不含自身。
 * 分类不存在、parent_id 缺失或指向不存在的父级时回空数组——前台据此不显面包屑。
 */
export function categoryAncestorPath<T extends CategoryTreeRow>(
  items: readonly T[],
  id: number | string | null | undefined
): T[] {
  const byId = new Map<string, T>()
  for (const item of items) {
    const k = rowKey(item.id)
    if (k && !byId.has(k)) byId.set(k, item)
  }
  const start = rowKey(id)
  const current = start ? byId.get(start) : undefined
  if (!current) return []

  const path: T[] = []
  const visited = new Set<string>([start])
  let cursor = byId.get(rowKey(current.parent_id))
  while (cursor) {
    const k = rowKey(cursor.id)
    if (visited.has(k)) break
    visited.add(k)
    path.unshift(cursor)
    cursor = byId.get(rowKey(cursor.parent_id))
  }
  return path
}

/** 某行的直接子分类（保持输入顺序）。 */
export function categoryChildren<T extends CategoryTreeRow>(
  items: readonly T[],
  id: number | string | null | undefined
): T[] {
  const key = rowKey(id)
  if (!key) return []
  return items.filter(item => rowKey(item.parent_id) === key && rowKey(item.id) !== key)
}
