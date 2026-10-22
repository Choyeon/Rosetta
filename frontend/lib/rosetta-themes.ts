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

/**
 * i18n prefix_except_default 策略：默认语言 zh 走裸路径，其余三语在 URL 上挂前缀。
 *
 * 这份清单是全仓**唯一**的语言前缀真源。历史上它在 12 处各写一份（4 个中间件、
 * 2 个插件、nuxt.config 镜像表、3 个 Nitro server 文件、useSeo），加一种语言或
 * 改一个前缀要同时数对十二个地方；漏一处的表现都静默——带前缀的后台被判成前台页、
 * /en/login 读不到服务端 noindex、非法归档年在 /ja 下返回 200 并被 swr 缓存。
 * 新增消费方一律 import 本模块，禁止再写语言前缀的字面量正则或数组副本。
 */
export const NON_DEFAULT_LOCALE_CODES = ['en', 'ja', 'zh_Hant'] as const

/** 语言码对应的 URL 前缀形态（/en、/ja、/zh_Hant）。 */
export const I18N_URL_PREFIXES: readonly string[] = NON_DEFAULT_LOCALE_CODES.map(
  code => `/${code}`
)

/** robots.txt 这类纯前缀拼接需要的全部形态：默认语言裸路径 + 三个前缀。 */
export const LOCALE_PATH_PREFIX_VARIANTS: readonly string[] = ['', ...I18N_URL_PREFIXES]

/** prefix_except_default 里走裸路径的那一方（nuxt.config 的 defaultLocale 同值）。 */
export const DEFAULT_LOCALE_CODE = 'zh'

/**
 * URL 路径 → 语言码（prefix_except_default 的反向算术）。
 *
 * 「当前这一页是什么语言」的唯一真相就是 URL 前缀（AGENTS §2.3.3.6），所以任何
 * 拿不到 Nuxt i18n 上下文的地方（事件回调、独立插件、非 setup 期的请求）都用这个，
 * 不要再读 localStorage / navigator.language / rosetta_lang cookie —— 那三样记录的是
 * "浏览器偏好"或"上次去的语言"，与当前这一页无关；按它们发请求的实测表现是
 * 简体页面拿到繁体接口数据，SSR 先渲简体、客户端补拉后翻回繁体。
 */
export function localeCodeFromPath(path: string | undefined | null): string {
  if (!path) return DEFAULT_LOCALE_CODE
  const hit = NON_DEFAULT_LOCALE_CODES.find(
    code => path === `/${code}` || path.startsWith(`/${code}/`)
  )
  return hit ?? DEFAULT_LOCALE_CODE
}

/**
 * 剥掉开头的语言前缀，得到"中性"路径。只认整段：/encyclopedia 不是 /en 前缀。
 * 空/undefined 返回 ''（调用方按"无路径"处理）。
 */
export function stripLocalePathPrefix(path: string | undefined | null): string {
  if (!path) return ''
  for (const p of I18N_URL_PREFIXES) {
    if (path === p) return '/'
    if (path.startsWith(p + '/')) return path.slice(p.length)
  }
  return path
}

/** 路径是否已经带语言前缀（整段匹配，/en-post 不算）。 */
export function hasLocalePathPrefix(path: string | undefined | null): boolean {
  if (!path) return false
  return I18N_URL_PREFIXES.some(p => path === p || path.startsWith(p + '/'))
}

/**
 * 路径是否命中某个站内根路径：等于它，或是它的子路径。
 * 必须显式比 `root + '/'`——裸 startsWith 会把 /admin-x 判进 /admin、
 * /login-x 判进 /login（这些是同前缀的独立路由，口径由回归用例钉着）。
 */
export function matchesPathRoot(path: string | undefined | null, root: string): boolean {
  if (!path) return false
  return path === root || path.startsWith(`${root}/`)
}

/** 与语言前缀无关的根路径命中判定：/en/admin 与 /admin 同页。 */
export function matchesNeutralRoot(path: string | undefined | null, root: string): boolean {
  return matchesPathRoot(stripLocalePathPrefix(path), root)
}

/** 路径是否命中主题视觉排除名单（前缀匹配，语言前缀不参与判定）。 */
export function isThemeVisualExcluded(path: string | undefined | null): boolean {
  if (!path) return false
  return THEME_VISUAL_EXCLUDE_PREFIXES.some(prefix => matchesNeutralRoot(path, prefix))
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
