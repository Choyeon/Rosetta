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
 * 导航行 → 可渲染链接：标签取不到当前语言文案的行直接丢（空链接比缺链接更糟），
 * URL 走 normalizeNavRowUrl，外链保留原样。target_blank 不再参与判定（口径见 AppHeader）。
 */
export function navRowsToLinks(
  rows: unknown,
  labelOf: (row: NavApiRow) => string
): NavLink[] {
  if (!Array.isArray(rows)) return []
  const out: NavLink[] = []
  for (const raw of rows as NavApiRow[]) {
    const label = labelOf(raw)
    if (!label) continue
    const to = normalizeNavRowUrl(raw)
    if (!to) continue
    out.push({ label, to })
  }
  return dedupeByTo(out)
}
