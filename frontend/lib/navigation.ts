/**
 * 前台导航项的形状与高亮判定（顶栏 / 移动抽屉 / 侧边栏导航共用一份）。
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

export function isNavActive(currentPath: string, to: string): boolean {
  if (!to || /^https?:\/\//i.test(to) || to.startsWith('#')) return false
  const current = stripLocalePathPrefix(currentPath)
  if (to === '/') return current === '/'
  return current === to || current.startsWith(to + '/')
}
