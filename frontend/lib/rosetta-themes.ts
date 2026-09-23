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

/**
 * 极简主题（astro-paper-inspired 一族）slug 集合——单一权威来源。
 *
 * 页头/页脚/登录/注册/错误页/首页网格等组件用它切换"极简变体"渲染。
 * 历史上该 Set 在 6 个组件里各写一份，新增极简系主题时必然漏改；现统一从这里导入。
 */
export const MINIMAL_THEME_SLUGS: ReadonlySet<string> = new Set(['astro-paper-inspired'])

/**
 * 永不应用主题视觉层的路径前缀（单一权威来源）。
 *
 * 消费方（必须保持同一份语义，历史上两处各写各的导致 /oobe 行为不一致）：
 *   1. composables/useFrontendTheme.ts —— applyThemeVisual 的排除判定
 *   2. middleware/layout-scope.global.ts —— 这些路径统一写 data-layout-scope="admin"
 *      并触发 DOM 残留清理
 */
export const THEME_VISUAL_EXCLUDE_PREFIXES: readonly string[] = ['/admin', '/oobe']

/** 路径是否命中主题视觉排除名单（前缀匹配）。 */
export function isThemeVisualExcluded(path: string | undefined | null): boolean {
  if (!path) return false
  return THEME_VISUAL_EXCLUDE_PREFIXES.some(prefix => path.startsWith(prefix))
}

/**
 * 主题静态资源路径归一（screenshot / style.css 等共享单一来源）。
 *
 * manifest 里的 screenshot_urls / 样式引用允许三种书写：
 *   1) 裸文件名：screenshot.svg → `/themes/<slug>/screenshot.svg`
 *   2) 根相对：/xxx.png → 原样（前端 public 或其它已挂载路径）
 *   3) 绝对 URL：https://... → 原样（外链 CDN/OSS）
 *
 * 历史上 useFrontendTheme（复数版）与 ThemeManager（单数版）各写一份归一逻辑，
 * 规则漂移会导致同一 manifest 在前台预览与后台卡片渲染出不同 URL。
 */
export function resolveThemeAssetPath(slug: string | null | undefined, src: string): string {
  if (!src) return ''
  if (/^https?:\/\//i.test(src) || src.startsWith('/')) return src
  return slug ? `/themes/${slug}/${src}` : ''
}

/**
 * 给本地 `/themes/**` 资源追加版本 query（强缓存 bust）。
 *
 * nuxt.config 给 `/themes/**` 配了 `max-age=31536000, immutable`，若不带上
 * `?v=<version>`，主题升级换掉 style.css / screenshot 后浏览器仍命中旧缓存、
 * 永不重新拉取。外链与根路径原样返回（它们不由主题目录版本管理）。
 */
export function bustThemeAssetCache(url: string, version?: string | null): string {
  if (!url || !url.startsWith('/themes/')) return url
  const v = encodeURIComponent(version || '0')
  return `${url}${url.includes('?') ? '&' : '?'}v=${v}`
}
