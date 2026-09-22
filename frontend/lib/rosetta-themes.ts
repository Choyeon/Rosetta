/**
 * Rosetta 内建主题 slug 单一权威来源（与 frontend/themes/ 目录一一对应）。
 *
 * 用途：判定 <html data-theme="..."> 的值是否由 Rosetta 主题系统写入——
 * 只有"我们的"值才允许在 admin 布局 / layout-scope 清理时被移除，
 * 避免误删明暗模式（light/dark）等非主题属性。
 *
 * ⚠️ 新增/删除内建主题（frontend/themes/<slug>/）时必须同步登记到这里：
 *    1. useFrontendTheme.ts（import 本模块）
 *    2. middleware/layout-scope.global.ts（import 本模块）
 * 后端默认激活候选（core/extensions.py 的 candidates）与前端无关，独立维护。
 */
export const KNOWN_ROSETTA_THEMES: ReadonlySet<string> = new Set([
  'editorial-wp-style',
  'astro-paper-inspired'
])
