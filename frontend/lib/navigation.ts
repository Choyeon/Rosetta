/**
 * 前台导航项的形状与高亮判定（顶栏 / 移动抽屉 / 侧边栏导航 / 页脚共用一份）。
 *
 * 高亮必须先把语言前缀剥掉再比：导航项的 `to` 是中性路径（`/posts`），
 * 而 `route.path` 在 en/ja/zh_Hant 下是 `/en/posts`——不剥前缀时英文页面上
 * 整条导航都不亮，中文首页那条还会反过来误亮。
 */
import { stripLocalePathPrefix } from './rosetta-themes'

export interface NavLink {
  label: string
  to: string
  target?: string
  /**
   * 菜单图标（`NavigationResponse.icon`，heroicons 名或 emoji）。
   * 后台一直能写这一栏，但此前四个渲染面一个都不读——图标只存在于后台表格里。
   * 空值时这个键不存在（渲染面用 `v-if="item.icon"`，不要传空串给 DynamicIcon）。
   */
  icon?: string
  /**
   * 二级菜单。后台 `parent_id` 指向本项的那些行；没有子项时这个键不存在
   * （渲染面用 `v-if="item.children?.length"`，不要写成 `children.length`）。
   */
  children?: NavLink[]
}

/**
 * `GET /navigations?location=<header|footer|sidebar>` 的一行。
 * 字段形态历史包袱见 AppHeader 的注释：url/to/href/path/slug 都可能带地址。
 */
export interface NavApiRow {
  id?: number | string
  label?: string | Record<string, string> | null
  title?: string | Record<string, string> | null
  name?: string | Record<string, string> | null
  url?: string
  to?: string
  href?: string
  path?: string
  slug?: string
  link_type?: string
  is_external?: boolean
  target?: string
  target_blank?: boolean
  /** 菜单图标（heroicons 名 / emoji / 纯文本），解析与降级在 DynamicIcon。 */
  icon?: string | null
  /** 父导航行 id（`NavigationResponse.parent_id`）。同一批返回里没有这个 id 时按顶层渲染。 */
  parent_id?: number | string | null
}

export function isNavActive(currentPath: string, to: string): boolean {
  if (!to || /^https?:\/\//i.test(to) || to.startsWith('#')) return false
  const current = stripLocalePathPrefix(currentPath)
  if (to === '/') return current === '/'
  return current === to || current.startsWith(to + '/')
}

/**
 * 规范化后端导航菜单返回的内部 URL 路径（顶栏、页脚、侧边栏三个消费面同一套）。
 * — 历史兼容：旧 Astro 站点和老数据会保存 "/page/about"、"/page/guestbook"
 *   等带 "/page/" 前缀的路径。Nuxt 前端静态页位于 pages/about.vue、
 *   pages/guestbook.vue 等（不含前缀）。需要移除前缀才能命中真实路由。
 * — 独立页 slug：当 link_type==="page" 且字段含 slug 时，按 "/<slug>" 归一化。
 * — 末尾 "/"：除首页 "/" 外统一去重，避免 "/posts/" 和 "/posts" 被视为不同激活。
 */
export function normalizeNavRowUrl(row: NavApiRow): string {
  const picked = row.link_type === 'page' && row.slug
    ? `/${String(row.slug).replace(/^\/+/, '')}`
    : String(row.to ?? row.url ?? row.href ?? row.path ?? row.slug ?? '').trim()
  if (!picked) return ''
  if (/^https?:\/\//i.test(picked)) return picked

  // 规范化：相对路径按内部路由处理，统一前缀 "/"
  let raw = picked
  if (!raw.startsWith('/') && !raw.startsWith('#')) {
    raw = `/${raw}`
  }
  // 兼容 "/page/<slug>" 旧前缀 → 折去 "/page"
  if (raw.startsWith('/page/')) raw = raw.slice('/page'.length) || '/'
  else if (raw === '/page') raw = '/'

  // 去重末尾斜杠（首页保留）
  if (raw.length > 1 && raw.endsWith('/')) raw = raw.slice(0, -1)
  return raw
}

/**
 * 去重：按 to 字段保留第一次出现（解决用户截图里「关于 × 2 连续出现」的问题）。
 * 页脚把「站点固定链接」和「后台配的页脚菜单」并排显示时，同一条 URL 只出现一次。
 */
export function dedupeByTo<T extends { to: string }>(arr: ReadonlyArray<T>): T[] {
  const seen = new Set<string>()
  const out: T[] = []
  for (const it of arr) {
    if (seen.has(it.to)) continue
    seen.add(it.to)
    out.push(it)
  }
  return out
}

/**
 * 导航行 → 可渲染链接（顶栏 / 页脚 / 侧边栏抽屉同一个构造函数）。
 * — 标签取不到当前语言文案的行直接丢（空链接比缺链接更糟）；URL 走 normalizeNavRowUrl。
 * — `target_blank` 按 WordPress 口径翻译成 `target="_blank"`，不再参与"是否进导航"的判定。
 * — `includeExternal: false`（顶栏用）把外链整行丢掉：顶栏把链接交给 `<NuxtLink :to>`，
 *   外链会走内部路由解析；页脚/侧边栏保留原样透传。
 * — `parent_id` 折叠成两层（见 nestNavRows）。
 * — `icon` 在这里（唯一构造点）归一后随链接一起下发：顶栏 / 页脚 / 侧边栏 / 移动抽屉
 *   四个渲染面共用同一份 NavLink，任何一处自己再去读原始行就会与这里漂移。
 */
export function navRowsToLinks(
  rows: unknown,
  labelOf: (row: NavApiRow) => string,
  options: { includeExternal?: boolean } = {}
): NavLink[] {
  if (!Array.isArray(rows)) return []
  const includeExternal = options.includeExternal ?? true
  const flat: FlatNavRow[] = []
  for (const raw of rows as NavApiRow[]) {
    const label = labelOf(raw)
    if (!label) continue
    const to = normalizeNavRowUrl(raw)
    if (!to) continue
    const external = /^https?:\/\//i.test(to) || raw.is_external === true || raw.link_type === 'external'
    if (external && !includeExternal) continue
    const link: NavLink = { label, to }
    if (isBlankTarget(raw)) link.target = '_blank'
    // 空串 / 纯空白 / null 都当"没有图标"：键整个不存在，渲染面一个节点都不输出。
    const icon = typeof raw.icon === 'string' ? raw.icon.trim() : ''
    if (icon) link.icon = icon
    flat.push({
      id: positiveId(raw.id),
      parentId: positiveId(raw.parent_id),
      link
    })
  }
  return nestNavRows(flat)
}

interface FlatNavRow {
  id: number | null
  parentId: number | null
  link: NavLink
}

/** `_blank` 的两种写法（布尔位 target_blank 与字符串 target）都要认。 */
function isBlankTarget(row: NavApiRow): boolean {
  return row.target_blank === true || row.target === '_blank'
}

/** 只有正整数 id 能参与父子匹配：0 / null / NaN / 字符串脏值一律当"没有 id"。 */
function positiveId(value: unknown): number | null {
  const n = Number(value)
  return Number.isInteger(n) && n > 0 ? n : null
}

/** 上溯预算只用于防病态数据（渲染只给一档缩进，层级深浅另说）。 */
const NAV_MAX_ANCESTRY_WALK = 20

/**
 * 上溯 parent_id 找本批里的根节点。
 * 返回 null 的三种情况都必须把该项留在顶层，而不是丢掉它：
 * 父行不在同一批（跨位置 / 已停用 / 已删除）、父行指向自己或成环、链太深。
 */
function findRoot(
  row: FlatNavRow,
  byId: Map<number, FlatNavRow>
): FlatNavRow | null {
  if (row.parentId == null) return null
  let current = row
  let depth = 0
  const visited = new Set<number>()
  for (;;) {
    const parent = current.parentId == null ? undefined : byId.get(current.parentId)
    if (!parent) break
    if (parent.id != null && (visited.has(parent.id) || depth >= NAV_MAX_ANCESTRY_WALK)) return null
    if (parent.id != null) visited.add(parent.id)
    current = parent
    depth += 1
  }
  return depth === 0 ? null : current
}

/**
 * 把带 parent_id 的扁平行折叠成"父 + 子"两层。
 *
 * 后台能写 parent_id、列表也打「二级菜单」徽标，但四个渲染面此前一律平铺——
 * 菜单层级只存在于后台表格里，属于「有声明、无执行者」。三条不丢链接的规则：
 *   ① 先按 URL 去重再折叠：父行若因为重复被丢，它的子项会退回顶层（不会跟着一起消失）；
 *   ② 父行不在同一批 / 自指 / 成环 / 超深 → 该项留在顶层；
 *   ③ 第 2 层及更深的后代并进根的 children：渲染只给一档缩进，
 *      宁可少一层视觉层级，也不让菜单项因为"没地方缩进"而消失。
 */
export function nestNavRows(rows: ReadonlyArray<FlatNavRow>): NavLink[] {
  const unique: FlatNavRow[] = []
  const seenTo = new Set<string>()
  for (const row of rows) {
    if (seenTo.has(row.link.to)) continue
    seenTo.add(row.link.to)
    unique.push(row)
  }

  const byId = new Map<number, FlatNavRow>()
  for (const row of unique) {
    if (row.id != null && !byId.has(row.id)) byId.set(row.id, row)
  }

  const roots: FlatNavRow[] = []
  const childrenByRoot = new Map<FlatNavRow, NavLink[]>()
  for (const row of unique) {
    const root = findRoot(row, byId)
    if (root) {
      const bucket = childrenByRoot.get(root) ?? []
      bucket.push(row.link)
      childrenByRoot.set(root, bucket)
      continue
    }
    roots.push(row)
  }

  return roots.map((rootRow) => {
    const children = childrenByRoot.get(rootRow)
    return children && children.length > 0 ? { ...rootRow.link, children } : rootRow.link
  })
}

/**
 * 去掉与另一份清单重复的链接。父项因为重复被摘掉时，子项上提一层而不是跟着消失——
 * 侧边栏抽屉把 header 档和 sidebar 档分两节显示，同一 URL 只该出现一次，
 * 但"父项正好也在上一节里"不该让整支子菜单一起不见了（缺入口比缺层级更糟）。
 */
export function withoutDuplicateTos(
  links: ReadonlyArray<NavLink>,
  taken: ReadonlySet<string>
): NavLink[] {
  const out: NavLink[] = []
  for (const link of links) {
    const children = link.children?.length ? withoutDuplicateTos(link.children, taken) : []
    if (taken.has(link.to)) {
      out.push(...children)
      continue
    }
    const self: NavLink = { label: link.label, to: link.to }
    if (link.target) self.target = link.target
    if (link.icon) self.icon = link.icon
    out.push(children.length > 0 ? { ...self, children } : self)
  }
  return out
}

/** 带层级的平铺行：`depth` 0 = 顶层，1 = 二级（渲染面用它做一档缩进）。 */
export interface NavListRow extends NavLink {
  depth: number
}

/**
 * 父在前、子紧随的平铺表（深度优先）。
 * 抽屉 / 页脚 / 移动菜单用它而不是嵌套 `<ul>`：一档缩进就能表达两层，
 * 且每个子项在 SSR HTML 里都是真实 `<a>`——爬虫读到的是完整内链图。
 */
export function flattenNavLinks(
  links: ReadonlyArray<NavLink>,
  depth = 0
): NavListRow[] {
  const out: NavListRow[] = []
  for (const link of links) {
    out.push({ ...link, depth })
    if (link.children?.length) out.push(...flattenNavLinks(link.children, depth + 1))
  }
  return out
}
