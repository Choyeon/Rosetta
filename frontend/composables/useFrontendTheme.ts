/**
 * useFrontendTheme
 * -----------------
 * 读取当前公开启用的 Rosetta 主题（GET /api/themes/active），把它的 mods / slug / schema
 * 以 SSR-safe 的 useState 形式暴露给全站。
 *
 * 主题 mods 与 settings 的职责划分（2026-11 解耦）：
 *   - 主色 primary_color：theme 写入 --theme-primary-hsl（主题专属命名空间），
 *     绝不碰系统 --primary。主题 CSS 可 `--primary: var(--theme-primary-hsl, <回退>)
 *     !important` 主动接管系统主色；未激活主题时系统 --primary 由 settings/CSS 定义。
 *   - 强调色 accent_color：theme 写入 --theme-accent-hue/sat/light（主题专属）。
 *   - 内容区宽度 layout_width：theme 写入 --rosetta-layout-width（主题专属）。
 *   - Hero 大标题 / 副标题：theme 若定义则覆盖 settings.hero（文案部分）
 *   - 页脚版权文字：theme 若定义则覆盖 settings.footer
 *   - 侧边栏开关 / 位置、首页每行文章数、作者卡、相关文章：theme 独立来源
 *   - 若没有任何主题 active → 全部 fallback 到 settings 默认值
 *
 * 数据安全：
 *   - 所有派生值均放在 computed 内；即使公共接口偶发失败，也永远返回定义了类型的默认值，
 *     不会让调用方遇到 undefined 导致 hydration mismatch。
 */
import { apiFetch } from '~~/composables/useApi'
import { hexToHsl } from '~~/lib/utils'
import { bustThemeAssetCache, clampThemeWidth, isThemeVisualExcluded, KNOWN_ROSETTA_THEMES, resolveThemeAssetPath } from '~~/lib/rosetta-themes'

type JsonObject = Record<string, unknown>

export interface FrontendThemeInfo {
  slug: string | null
  name: string | null
  version: string | null
  screenshot_urls: string[]
  mods: ThemeModsRuntime
  mods_schema: JsonObject | null
  loaded: boolean
  /** 主题 manifest 的 tags 数组（如 ["minimal"]），供前端派生渲染变体。
   *  不再用硬编码 slug 集合判定主题族系——新主题只需在 manifest 里声明 tag 即可被识别。 */
  tags: string[]
  /** 处于「预览模式」：slug 来自 ?rosetta_theme_preview= 查询参数而非后端 active 主题。 */
  previewing: boolean
}

/** 与 editorial-wp-style rosetta-theme.json 一致；未来新主题新增键这里可以不立刻改动。 */
export interface ThemeModsRuntime {
  hero_title: string
  hero_subtitle: string
  layout_width: number
  show_sidebar: boolean
  sidebar_position: 'left' | 'right'
  /** 1~6 的整数。旧版本硬编码 2|3|4，会把极简主题的 1 列配置误杀回默认 3。 */
  posts_per_row: number
  accent_color: string
  primary_color: string
  show_author_box: boolean
  show_related_posts: boolean
  show_avatar: boolean
  footer_text: string
  [k: string]: unknown
}

const MODS_DEFAULTS: ThemeModsRuntime = {
  hero_title: '',
  hero_subtitle: '',
  layout_width: 1200,
  show_sidebar: true,
  sidebar_position: 'right',
  posts_per_row: 3,
  accent_color: '',
  primary_color: '',
  show_author_box: true,
  show_related_posts: true,
  show_avatar: true,
  footer_text: ''
}

/**
 * 【默认主题 = 平级主题包 · 2026-09 架构解耦】
 * editorial-wp-style 的视觉皮肤完整存放在自己的 style.css（main.css 已退化为
 * 主题中性基础设施）。当后端"无激活主题"或 /themes/active 请求失败时，
 * 前台回退加载这份默认主题，保证渲染路径上永远恰好有一个完整主题 CSS。
 * version 必须与 themes/editorial-wp-style/rosetta-theme.json 保持同步
 * （用作 style.css ?v= 缓存击穿键）。
 */
export const DEFAULT_THEME_SLUG = 'editorial-wp-style'
export const DEFAULT_THEME_NAME = '默认主题'
export const DEFAULT_THEME_VERSION = '1.2.0'

const useThemeState = () =>
  useState<FrontendThemeInfo>('frontend-theme:state', () => ({
    // 初始即指向默认主题：SSR 兜底（后端故障 / 无激活主题）下首字节
    // 仍能渲染出完整主题皮肤，而非中性骨架。ensureLoaded 成功后被真实值覆盖。
    slug: DEFAULT_THEME_SLUG,
    name: DEFAULT_THEME_NAME,
    version: DEFAULT_THEME_VERSION,
    screenshot_urls: [],
    mods: { ...MODS_DEFAULTS },
    mods_schema: null,
    loaded: false,
    tags: [],
    previewing: false
  }))

function mergeMods(mods: unknown): ThemeModsRuntime {
  const out: ThemeModsRuntime = { ...MODS_DEFAULTS }
  if (!mods || typeof mods !== 'object' || Array.isArray(mods)) return out
  const raw = mods as JsonObject
  for (const k of Object.keys(MODS_DEFAULTS) as (keyof ThemeModsRuntime)[]) {
    const v = raw[k]
    switch (k) {
      case 'layout_width': {
        // 区间与默认值单源在 lib/rosetta-themes::clampThemeWidth（640–1200，兜底 880）。
        // 键缺失 / 空值时保留 MODS_DEFAULTS（editorial 语义的 1200），不被动钳到 880；
        // 越界值由 clamp 贴边收敛，不再整条退回默认。
        if (v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v)))
          out.layout_width = clampThemeWidth(v)
        break
      }
      case 'posts_per_row': {
        const n = Number(v)
        if (Number.isInteger(n) && n >= 1 && n <= 6) out.posts_per_row = n
        break
      }
      case 'show_sidebar':
      case 'show_author_box':
      case 'show_related_posts':
      case 'show_avatar':
        if (typeof v === 'boolean') out[k] = v
        break
      case 'sidebar_position':
        if (v === 'left' || v === 'right') out.sidebar_position = v
        break
      case 'hero_title':
      case 'hero_subtitle':
      case 'accent_color':
      case 'primary_color':
      case 'footer_text':
        if (typeof v === 'string') out[k] = v
        break
    }
  }
  // 主题特有 mods（MODS_DEFAULTS 未声明的键，如 astro 的 1 列配置之外的扩展项）
  // 原样透传——组件可经 mods 的 [k: string]: unknown 索引访问，不再被静默丢弃。
  for (const k of Object.keys(raw)) {
    if (!(k in MODS_DEFAULTS)) out[k] = raw[k]
  }
  return out
}

/**
 * 主题 style.css 的 URL 单一构造点。
 *
 * nuxt.config routeRules 对 /themes/** 发 `max-age=31536000, immutable` 强缓存，
 * 不带版本号的 URL 意味着主题升级后访客永远拿到旧 CSS——必须携带 ?v=<theme.version>
 * 做 cache-busting。SSR（useHead）与客户端 DOM 注入两条路径都走本函数，保证
 * href 完全一致、不产生双 <link>。
 */
function themeCssHref(slug: string, version?: string | null): string {
  return bustThemeAssetCache(resolveThemeAssetPath(slug, 'style.css'), version)
}

/**
 * 主题色 token 写入（2026-11 解耦重构）。
 *
 * 设计原则：主题 mods 的颜色**只写进主题专属命名空间**（`--theme-*`），
 * 绝不直接覆盖系统 `--primary` / `--ring`。这样：
 *   · 当主题未激活 / primary_color 为空时，系统 `--primary`（main.css :root 定义
 *     或 settings.appearance 写入）保持原样，"默认系统主题"不受任何主题干扰；
 *   · 主题若想让自己的主色影响系统组件（按钮/链接等），必须在自己的 style.css 里
 *     显式声明 `--primary: var(--theme-primary-hsl, <系统回退>)`——这是主题作者的
 *     主动选择，不是框架的强制行为；
 *   · `_clearThemeVisual` 只需移除 `--theme-*` 变量，系统 token 自动恢复，
 *     不再需要"标记属性 + 启发式判断值来源"那套脆弱机制。
 *
 * 写入的变量：
 *   · `--theme-accent-hue/sat/light`：主题强调色（HSL 分量，供主题 CSS 消费）
 *   · `--theme-primary-hsl`：主题主色（HSL 三元组字符串，如 "199 100% 33%"）
 *   · `--rosetta-layout-width`：主题版心宽度（主题专属，不影响系统）
 *
 * 【SSR 策略】
 * ensureLoaded() 里调用 apply* 发生在 `await apiFetch(...)` 之后——Nuxt SSR
 * async setup 在"第一个 await 之后"丢失同步 NuxtApp 上下文，之后调 useHead 会
 * 触发 NUXT_E1001。SSR 端的颜色 token 注入在 useFrontendTheme() 首次创建时（同步
 * 阶段）通过 `registerFrontendThemeHead()` 的 reactive useHead 完成；本函数仅在
 * 客户端 DOM 直接写（优先级最高，是最终值）。
 */
function applyThemeColorTokens(mods: ThemeModsRuntime) {
  if (import.meta.server) return
  if (!import.meta.client) return
  const root = document.documentElement
  if (mods.accent_color) {
    const hsl = hexToHsl(mods.accent_color)
    if (hsl) {
      root.style.setProperty('--theme-accent-hue', String(Math.round(hsl.h)))
      root.style.setProperty('--theme-accent-sat', `${Math.round(hsl.s)}%`)
      root.style.setProperty('--theme-accent-light', `${Math.round(hsl.l)}%`)
    }
  }
  if (mods.layout_width) {
    root.style.setProperty('--rosetta-layout-width', `${Number(mods.layout_width)}px`)
  }
  // 主题主色只写入 --theme-primary-hsl，绝不碰 --primary / --ring。
  // 主题 style.css 可通过 `--primary: var(--theme-primary-hsl, <fallback>)` 主动接管。
  if (mods.primary_color) {
    const hsl = hexToHsl(mods.primary_color)
    if (hsl) {
      root.style.setProperty(
        '--theme-primary-hsl',
        `${Math.round(hsl.h)} ${Math.round(hsl.s)}% ${Math.round(hsl.l)}%`
      )
    }
  }
}

/**
 * 永不可应用主题视觉层的路径判定见 lib/rosetta-themes 的 THEME_VISUAL_EXCLUDE_PREFIXES
 * （/admin、/oobe）——与 middleware/layout-scope.global.ts 共用单一来源。
 *
 * 2026-09 调整：/login 与 /register 从排除名单移出。它们的 data-layout-scope
 * 是 "public-auth"（而非 "frontend"），主题 style.css 的既有规则全部带
 * [data-layout-scope="frontend"] 守卫、在认证页上不命中；因此这里允许注入
 * slug 属性 + <link>，供主题 CSS 中显式书写的 public-auth 段落（极简登录/
 * 注册页、toast 统一）消费，零耦合约束依旧成立。
 */
function _isFrontendExcludedPath(path?: string, routeFallbackPath?: string): boolean {
  // 注意：本函数**禁止在内部调用 useRoute()**——它会在 layouts/default.vue 的
  // async setup 等待 apiFetch 之后才被调度，而 "after await" 的 SSR 微任务阶段
  // 会异步丢失 NuxtApp 同步上下文 → NUXT_E1001。
  // 所有调用方（ensureLoaded / applyThemeVisual / clearThemeVisual）必须显式传 path。
  let p: string | undefined
  if (path) {
    p = path
  } else if (routeFallbackPath) {
    p = routeFallbackPath
  } else if (import.meta.client && typeof window !== 'undefined') {
    p = window.location.pathname
  }
  return isThemeVisualExcluded(p)
}

/**
 * 所有曾注入过的主题 style.css <link> 注册表（slug → HTMLLinkElement）。
 * 共享给 _clearThemeVisual（admin 清理）与 applyThemeVisual（前台加载/切换）两边共同使用。
 * 【声明位置必须在 _clearThemeVisual 之前，避免 TDZ 错误】
 */
const _INSTALLED_LINKS = new Map<string, HTMLLinkElement>()

/** 手动兜底 <link> 的标记属性（区别于 unhead 注入的正主节点）。 */
const MANUAL_ATTR = 'data-rosetta-manual'

/**
 * 【单一手动兜底节点】跨 slug 复用同一个 <link> 元素、只切换 href——
 * 手动路径全生命周期最多存在一个节点，天然杜绝"多次 install 叠出多个兜底 link"。
 */
let _manualLink: HTMLLinkElement | null = null
/** 当前手动兜底节点服务的 slug（用于精确回收 _INSTALLED_LINKS 中的登记项）。 */
let _manualLinkSlug: string | null = null
/**
 * 【事件驱动移交】unhead 响应式节点到位前，用 MutationObserver 监听 <head>；
 * 正主一出现立即摘除兜底并认领——取代历史 setTimeout(400) 定时竞态
 * （400ms 不是"就绪信号"只是经验值：unhead 晚于 400ms flush 时兜底与正主
 * 双 <link> 长期共存重复加载，且旧定时器在 slug 切换/清理后仍会迟到触发）。
 */
let _handoffObserver: MutationObserver | null = null

function _stopHandoff() {
  if (_handoffObserver) {
    _handoffObserver.disconnect()
    _handoffObserver = null
  }
}

function _removeManualLink() {
  _stopHandoff()
  if (_manualLink) {
    if (_manualLinkSlug) _INSTALLED_LINKS.delete(_manualLinkSlug)
    _manualLink.remove()
    _manualLink = null
    _manualLinkSlug = null
  }
}

/**
 * 若 unhead 正主节点（id=rosetta-theme-css-<slug>）已在 <head> 中：
 * 摘除同 slug 的手动兜底、认领正主。返回是否完成认领（供移交观察器判定）。
 *
 * 认领前置条件：节点 href 与当前构造的 wantHref 完全一致——
 * 主题 CSS 走 immutable 强缓存，unhead 在 flush 窗口内可能仍持有上一
 * slug/version 的旧节点；认领 stale 节点再摘兜底会导致主题 CSS 掉帧
 * （白屏一瞬）。unhead 的响应式 flush 完成后本观察器会再次命中新版本节点。
 */
function _adoptCanonicalLink(slug: string, wantHref: string): boolean {
  const headLink = document.querySelector<HTMLLinkElement>(
    `link[rel="stylesheet"][id="rosetta-theme-css-${slug}"]`
  )
  if (!headLink) return false
  // 版本核对：unhead 在 flush 窗口内可能仍持有上一 slug/version 的旧节点，
  // 只有 href 与当前构造完全一致才算"服务本版本的正主"。
  const href = headLink.getAttribute('href') || ''
  if (href !== wantHref) return false
  if (_manualLink && _manualLinkSlug === slug) {
    _INSTALLED_LINKS.delete(slug)
    _removeManualLink()
  }
  _INSTALLED_LINKS.set(slug, headLink)
  _stopHandoff()
  return true
}

function _startHandoff(slug: string, wantHref: string) {
  _stopHandoff()
  if (typeof MutationObserver === 'undefined' || typeof document === 'undefined') return
  _handoffObserver = new MutationObserver(() => {
    // 观察回调里重新核对 href：unhead 可能先挂旧版本节点、随后原地更新，
    // 只有命中当前 wantHref 的节点才是可以接班的正主。
    if (_adoptCanonicalLink(slug, wantHref)) _stopHandoff()
  })
  _handoffObserver.observe(document.head, {
    childList: true,
    subtree: true,
    // unhead 对已收养的同 id 节点可能原地更新 href（主题升级 ?v=）而非重新插入，
    // 只监听 childList 会错过这种移交时机。
    attributes: true,
    attributeFilter: ['href']
  })
}

/**
 * 匹配主题 slug class 的正则：`theme-` 后接小写字母/数字/连字符。
 * 故意不匹配 `theme-grow` / `theme-shrink`（明暗切换过渡 class，归 useTheme 管）。
 * 不再依赖 KNOWN_ROSETTA_THEMES 硬编码白名单——市场安装的新主题 slug 同样能被清理。
 */
const THEME_SLUG_CLASS_RE = /^theme-[a-z0-9]+(?:-[a-z0-9]+)*$/

/**
 * 移除 Rosetta 主题写入的 `theme-{slug}` class。
 * 用 slug 模式匹配而非白名单，保证未知主题（市场安装）也能被精确清理，
 * 同时绝不误伤 `theme-grow` / `theme-shrink`（useTheme 的明暗切换过渡 class）。
 */
function _removeRosettaThemeClasses(root: HTMLElement) {
  const toRemove: string[] = []
  for (const cls of root.classList) {
    if (THEME_SLUG_CLASS_RE.test(cls) && cls !== 'theme-grow' && cls !== 'theme-shrink') {
      toRemove.push(cls)
    }
  }
  for (const cls of toRemove) root.classList.remove(cls)
}

/**
 * 彻底清理 <html> 上的 Rosetta 主题视觉痕迹：
 *   · theme-{slug} class（slug 模式匹配，保留 theme-grow/theme-shrink）
 *   · data-rosetta-theme 属性
 *   · data-theme 属性（仅当值非系统明暗值 light/dark 时移除，避免破坏 useTheme）
 *   · 已注入的 /themes/<slug>/style.css <link>
 *   · 主题专属命名空间变量（--theme-* / --rosetta-layout-width）
 *
 * 【不触碰系统 token】：绝不移除 --primary / --ring——它们由 main.css :root 定义
 * 或 settings.appearance 管理，主题系统不再直接写它们（2026-11 解耦）。
 * 清理 --theme-* 后，系统 --primary 自动恢复为 CSS 定义值或 settings 值。
 *
 * 此函数 idempotent，admin 布局 onMounted / 路由切换时主动调用，保证后台永远是
 * shadcn 原生样式，不被前端主题 CSS 误伤。
 */
function _clearThemeVisual() {
  if (!import.meta.client) return
  const root = document.documentElement

  // 1) 清理 class（slug 模式匹配，不按 theme- 前缀盲删）
  _removeRosettaThemeClasses(root)

  // 2) 清理 data-* 属性
  root.removeAttribute('data-rosetta-theme')
  const currentDT = root.getAttribute('data-theme')
  // 仅移除非系统明暗值（light/dark 由 useTheme 管理，不归主题系统管）
  if (currentDT && currentDT !== 'light' && currentDT !== 'dark') {
    root.removeAttribute('data-theme')
  }

  // 3) 清理 <link>（含已被 unhead/中间件摘走、Map 里剩的失联节点）
  _removeManualLink()
  for (const [k, el] of _INSTALLED_LINKS) {
    el.remove()
    _INSTALLED_LINKS.delete(k)
  }

  // 4) 清理主题专属命名空间变量（绝不碰 --primary / --ring）
  root.style.removeProperty('--theme-accent-hue')
  root.style.removeProperty('--theme-accent-sat')
  root.style.removeProperty('--theme-accent-light')
  root.style.removeProperty('--theme-primary-hsl')
  root.style.removeProperty('--rosetta-layout-width')
}

/**
 * 归一 manifest.screenshot_urls 为可渲染 URL 列表。
 * 相对/根/绝对三种书写的解析规则统一在 lib 的 resolveThemeAssetPath。
 */
function normalizeScreenshotUrls(slug: string | null, raws: unknown): string[] {
  if (!Array.isArray(raws)) return []
  const out: string[] = []
  for (const r of raws) {
    if (typeof r !== 'string' || !r) continue
    const resolved = resolveThemeAssetPath(slug, r)
    if (resolved) out.push(resolved)
  }
  return out
}
function applyThemeVisual(slug: string | null, version?: string | null, explicitPath?: string) {
  // ===== SSR 策略：同步阶段 reactive useHead 已全权负责 =====
  // 见 useFrontendTheme() 导出函数顶部的 useHead(() => {…state.value…}) 注册。
  // ensureLoaded -> applyThemeVisual 的调用链发生在 await apiFetch 之后，
  // 此时 SSR 已丢失同步 NuxtApp 上下文，任何 useHead 调用都会触发 NUXT_E1001
  // 并连带子组件 undefined vnode 渲染失败。SSR 端直接 return。
  if (import.meta.server) return
  if (!import.meta.client) return
  // 【关键安全出口】admin / oobe 等禁止主题路径：
  // 不应用任何主题，反而彻底清理已写入的属性/链接/class，
  // 避免从前台 SPA 导航过来时 data-theme 等残留导致后台 UI 错乱。
  if (_isFrontendExcludedPath(explicitPath)) {
    _clearThemeVisual()
    return
  }

  const root = document.documentElement

  // 1) 先清理"旧 slug 不等于新 slug"的那部分（保留旧 link → 新 slug 相同命中缓存分支）
  _removeRosettaThemeClasses(root)
  root.removeAttribute('data-rosetta-theme')
  const currentDataTheme = root.getAttribute('data-theme')
  // 仅清理非系统明暗值（light/dark 由 useTheme 管理），不再依赖 KNOWN_ROSETTA_THEMES
  if (currentDataTheme && currentDataTheme !== 'light' && currentDataTheme !== 'dark') {
    root.removeAttribute('data-theme')
  }
  for (const [k, el] of _INSTALLED_LINKS) {
    if (k !== slug) {
      // 手动兜底节点走专用回收（同步置空 _manualLink / 断开移交观察器），
      // 否则会留下"已从 DOM 摘除但变量仍指向"的失联节点，破坏单一节点复用不变量。
      if (el === _manualLink) _removeManualLink()
      else {
        el.remove()
        _INSTALLED_LINKS.delete(k)
      }
    }
  }
  // 孤儿 <link> 兜底清理：SSR 强缓存页面的旧主题 link 由 Unhead 从 payload 收养，
  // 客户端纠偏换 slug 后 Unhead 的 reactive diff 不保证摘除它（实测会双 link 共存）。
  // 凡 id 命中标准前缀但不属于当前 slug 的主题样式表，一律视为陈旧节点移除。
  const keepId = slug ? `rosetta-theme-css-${slug}` : ''
  document
    .querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"][id^="rosetta-theme-css-"]')
    .forEach((el) => {
      if (el.id !== keepId) el.remove()
    })

  // 2) 去激活（没有 slug）→ 到此结束（上方已做清理）
  if (!slug) return

  // 3) 应用新 slug
  root.classList.add(`theme-${slug}`)
  root.setAttribute('data-rosetta-theme', slug)
  // 兼容 style.css 里广泛使用的 [data-theme="<slug>"] 前缀选择器。
  // 不覆盖明暗模式占用的 light/dark 值（useTheme 管理）。
  const existingDT = root.getAttribute('data-theme')
  if (!existingDT || (existingDT !== 'light' && existingDT !== 'dark')) {
    root.setAttribute('data-theme', slug)
  }

  // Map 里的节点必须"仍在 DOM 上且 href 命中当前版本"才算已安装；
  // 否则视为失联（被 unhead flush / 中间件摘走，或主题升级换了 ?v=），重新安装。
  const wantHref = themeCssHref(slug, version)
  const known = _INSTALLED_LINKS.get(slug)
  if (known?.isConnected && known.getAttribute('href') === wantHref) return
  if (known) {
    if (known === _manualLink) _removeManualLink()
    else known.remove()
    _INSTALLED_LINKS.delete(slug)
  }
  // 主题 <link> 有两个潜在来源：
  //   · useHead 响应式注入（SSR 首字节 / 客户端 slug 变化后由 unhead 批量 flush，
  //     其时机不确定，不能用一次同步检查判定）
  //   · 本函数的 DOM 直接注入（ssr:false 认证页 / error 页等纯客户端路径的兜底）
  // 策略（事件驱动，无定时竞态）：
  //   1. 先认领 head 中已存在的正主（id 命中且 href 等于当前版本）；
  //   2. 否则复用单一手动兜底节点（只切 href，不再新建第二个）；
  //   3. 用 MutationObserver 监听 <head>，正主 flush 到位的那一帧立即
  //      摘除兜底、认领正主——替代历史 setTimeout(400) 经验值移交
  //      （unhead 晚于 400ms flush 时双 link 长期共存重复加载；切换/清理后
  //      迟到的定时器还会操作已失效的节点）。
  // 移交观察器由 _clearThemeVisual / slug 切换 / 认领成功三处共同回收，无泄漏。
  if (!_adoptCanonicalLink(slug, wantHref)) {
    if (!_manualLink) {
      _manualLink = document.createElement('link')
      _manualLink.rel = 'stylesheet'
      _manualLink.setAttribute(MANUAL_ATTR, '1')
      _manualLink.onerror = () => {
        // 仅当失败的仍是当前服务中的兜底节点时回收（href 切换在途的旧 onerror 忽略）
        if (_manualLink && _manualLinkSlug && _INSTALLED_LINKS.get(_manualLinkSlug) === _manualLink) {
          _INSTALLED_LINKS.delete(_manualLinkSlug)
          _removeManualLink()
        }
      }
      document.head.appendChild(_manualLink)
    }
    _manualLinkSlug = slug
    _INSTALLED_LINKS.set(slug, _manualLink)
    _manualLink.setAttribute('href', wantHref)
    _startHandoff(slug, wantHref)
  }
}

/**
 * 对外暴露的清理入口：由 admin.vue / login.vue 等非前台布局调用，
 * 保证进入这些路由时 html 永远不保留 Rosetta 主题的视觉钩子。
 */
function clearThemeVisual() {
  _clearThemeVisual()
}

/**
 * ensureLoaded 的 in-flight 去重表：**以 NuxtApp 实例为键**，全 app 共享一个请求。
 *
 * 键必须是 NuxtApp 而不是 useState 返回的 ref：Nuxt 的 useState 实现是
 * `toRef(nuxtApp.payload.state, key)`，每次调用都新建一个 ObjectRefImpl 包装，
 * 所以每个 useFrontendTheme() 调用方拿到的是**不同的对象**。以 ref 为键时去重表
 * 只在同一个 composable 实例内命中——全站 10+ 个调用方等于 10+ 个独立键，首屏
 * 每个调用方各发一条。实测首页（plugin + layouts/default + pages/index 三处
 * 在 app:mounted 各排一次纠偏）稳定发出 3 条 GET /api/themes/active。
 * 用 WeakMap 而非模块级单值，避免 SSR 跨请求串用彼此的 state。
 */
const _ensureInflight = new WeakMap<object, Promise<FrontendThemeInfo>>()

/**
 * 记录"本客户端会话内真正发过请求并验证过"的 NuxtApp（同样不能用 ref 做键，见上）。
 * SSR payload hydrate 出来的 loaded=true 不算——公开页 HTML 可能来自 Nitro
 * SWR 缓存（'/' 300s，/archive 等最长 3600s），缓存窗口内后台可能已切换主题，
 * 若客户端无条件信任 hydrated 闩锁，页面会一直停留在旧主题直到缓存过期。
 * 因此客户端首次 ensureLoaded 必须补拉一次 /themes/active 做纠偏；同一会话内
 * 后续调用（SPA 路由切换）命中本集合，不再重复请求。
 */
const _clientFetched = new WeakSet<object>()

/** 已完成首帧挂载的客户端 app（仅纠偏调度用；SSR 恒不登记）。 */
const _appMounted = new WeakSet<object>()

/**
 * 【app 级唯一注册点】主题四件套（htmlAttrs / <link> / 颜色 token <style>）的响应式 head 入口。
 *
 * 为什么必须放在 app 级插件（plugins/01-site-bootstrap.global.ts）里、而不是
 * useFrontendTheme() 内部：
 *   · useHead() 在组件 setup 中调用会被绑定到该组件的 effect scope，组件卸载时
 *     unhead **dispose 整条 head entry**。全站有 10+ 处调用 useFrontendTheme()
 *     （layouts / pages / AppFooter / error.vue / useSite），每次 SPA 导航都会
 *     卸载旧页、挂载新页 → 多条持有同一 `rosetta-theme-css-<slug>` <link> 的
 *     entry 被反复 dispose / 重建，中间存在"head 里没有任何主题 <link>"的窗口
 *     → 浏览器以 main.css 的中性基座重绘一帧 → 观感就是「默认主题闪一下，
 *     然后极简主题又回来了」。
 *   · 02-hydration-safety 的 soft CSR remount（rootKey++）会整棵重挂组件树，
 *     同样触发上述 dispose 风暴；app 级 entry 不属于任何组件 scope，remount
 *     期间恒定存在，主题 <link> 永不掉落。
 *
 * 必须在 NuxtApp 上下文（插件 / setup）内调用，且整个 app 生命周期只调用一次。
 */
export function registerFrontendThemeHead() {
  const state = useThemeState()
  const route = useRoute()

  // =========================================================================
  // 【SSR 核心：同步阶段注册 reactive useHead】
  // 永远不要把 useHead() 放在 ensureLoaded() 的 await apiFetch(...) 之后调用——
  // Nuxt SSR async setup 在"第一个 await 之后"会丢失同步 NuxtApp 上下文，
  // 在此之后调 useHead 会触发 NUXT_E1001，子组件 VNode 会被渲染为 undefined。
  //
  // 注册之后，ensureLoaded 改写 state.value 的 slug / mods 变化都会被 Unhead
  // 自动追踪并响应式刷新 head / htmlAttrs，首字节 HTML 即包含主题四件套 +
  // 颜色 tokens，全程零 E1001。
  // =========================================================================
  useHead(() => {
    const s = state.value
    const excluded = isThemeVisualExcluded(route.path)

    // 1) htmlAttrs：data-rosetta-theme / data-theme / theme-{slug} class
    const htmlAttrs: Record<string, string> = {}
    // 3) style tokens 先构建（与 slug 无关的部分初始化）
    const styleTokens: string[] = []
    // 2) theme CSS <link>（条件命中后用字面量构造，let TS 推断精确 literal 类型）
    type LinkItem = { rel: 'stylesheet', href: string, id: string }
    let link: LinkItem[] = []

    if (s.slug && !excluded) {
      htmlAttrs['data-rosetta-theme'] = s.slug
      htmlAttrs['data-theme'] = s.slug
      htmlAttrs['class'] = `theme-${s.slug}`
      link = [
        {
          rel: 'stylesheet',
          href: themeCssHref(s.slug, s.version),
          id: `rosetta-theme-css-${s.slug}`
        }
      ]

      // accent → --theme-accent-hue/sat/light
      if (s.mods.accent_color) {
        const hsl = hexToHsl(s.mods.accent_color)
        if (hsl) {
          styleTokens.push(`--theme-accent-hue:${Math.round(hsl.h)}`)
          styleTokens.push(`--theme-accent-sat:${Math.round(hsl.s)}%`)
          styleTokens.push(`--theme-accent-light:${Math.round(hsl.l)}%`)
        }
      }
      // primary → --theme-primary-hsl（主题专属命名空间，不碰系统 --primary/--ring）
      if (s.mods.primary_color) {
        const hsl = hexToHsl(s.mods.primary_color)
        if (hsl) {
          styleTokens.push(
            `--theme-primary-hsl:${Math.round(hsl.h)} ${Math.round(hsl.s)}% ${Math.round(hsl.l)}%`
          )
        }
      }
      // layout width → --rosetta-layout-width（主题 CSS 消费窄栏宽度）
      if (s.mods.layout_width) {
        styleTokens.push(`--rosetta-layout-width:${Number(s.mods.layout_width)}px`)
      }
    }

    type StyleItem = { id: 'rosetta-theme-color-tokens', innerHTML: string }
    const style: StyleItem[] = styleTokens.length
      ? [{ id: 'rosetta-theme-color-tokens', innerHTML: `:root{${styleTokens.join(';')}}` }]
      : []

    return { htmlAttrs, link, style }
  })
}

export function useFrontendTheme() {
  const state = useThemeState()
  const route = useRoute()
  // 在 composable 创建（同步、上下文有效）时捕获 nuxtApp：纠偏调度要在 app:mounted 上挂 hook。
  const nuxtApp = useNuxtApp()

  const mods = computed<ThemeModsRuntime>(() => state.value.mods)
  const isActive = computed(() => !!state.value.slug)
  const slug = computed(() => state.value.slug)
  const name = computed(() => state.value.name)
  /** 主题 manifest 声明的 tags（如 ["minimal"]），单一来源：后端 /themes/active 返回值。 */
  const tags = computed<string[]>(() => state.value.tags)
  /** 当前主题是否为极简族系——由 manifest tags 含 "minimal" 派生，不再硬编码 slug 集合。
   *  新极简主题只需在 rosetta-theme.json 的 tags 里加 "minimal"，全站组件自动切换极简变体。 */
  const isMinimal = computed(() => state.value.tags.includes('minimal'))

  /** 主题显式设置了值，覆盖 / 合并上层 settings 的辅助开关（组件里直接用）。 */
  const override = {
    primary_color: computed(() => mods.value.primary_color || undefined),
    accent_color: computed(() => mods.value.accent_color || undefined),
    layout_width: computed(() => (isActive.value ? mods.value.layout_width : undefined)),
    hero_title: computed(() => mods.value.hero_title || undefined),
    hero_subtitle: computed(() => mods.value.hero_subtitle || undefined),
    footer_text: computed(() => mods.value.footer_text || undefined)
  }

  const showSidebar = computed(() => mods.value.show_sidebar)
  const sidebarPosition = computed(() => mods.value.sidebar_position)
  const postsPerRow = computed(() => mods.value.posts_per_row)
  const showAuthorBox = computed(() => mods.value.show_author_box)
  const showRelatedPosts = computed(() => mods.value.show_related_posts)
  const showAvatar = computed(() => mods.value.show_avatar !== false)
  const previewing = computed(() => state.value.previewing)

  /** 真实请求体：拉 /themes/active、写 state、应用颜色 token 与视觉层；并发调用共享 in-flight。 */
  function _startFetch(): Promise<FrontendThemeInfo> {
    const running = _ensureInflight.get(nuxtApp)
    if (running) return running
    const task = (async (): Promise<FrontendThemeInfo> => {
      let data: JsonObject | null = null
      let requestFailed = false
      // ── 预览模式：?rosetta_theme_preview=<slug> ──────────────────────────
      // 由后台「主题管理」的预览按钮打开新标签页触发。仅允许 KNOWN_ROSETTA_THEMES
      // 白名单内的 slug，覆盖 state.slug 以挂载该主题的 style.css + htmlAttrs，
      // 但不改动后端 active 主题。mods 沿用 active 主题（或默认值）——内建主题的
      // 视觉差异主要在 style.css，slug 覆盖即可得到忠实预览。
      // 必须在任何 await / 早退之前解析：请求失败分支也要能应用预览。
      const previewRaw = route.query.rosetta_theme_preview
      const previewSlug = Array.isArray(previewRaw) ? previewRaw[0] : previewRaw
      const wantPreview = typeof previewSlug === 'string' && KNOWN_ROSETTA_THEMES.has(previewSlug)
        ? previewSlug
        : null
      type ThemeActiveResp = { success: boolean, data: JsonObject | null }
      try {
        const resp = await apiFetch<ThemeActiveResp>('/themes/active', {
          method: 'GET',
          // 预览模式必须向服务端要**被预览主题自己**的 version / mods：
          // 否则 ?v= 缓存击穿键与 layout_width 等 mods 全部来自激活主题，
          // 预览出来的极简主题会套用默认主题的 1200px 版心、并挂在错误的
          // style.css 缓存键上。
          query: wantPreview ? { preview: wantPreview } : undefined,
          silentToast: true
        })
        data
          = resp && typeof resp === 'object' && (resp as ThemeActiveResp).success
            ? ((resp as ThemeActiveResp).data as JsonObject | null) ?? null
            : null
      } catch {
        // 网络/后端故障：与「成功但无激活主题」(data=null) 严格区分——
        // 前者不写 loaded 闩锁，下一次路由/组件仍会重试；后者正常落 latch。
        requestFailed = true
      }

      if (requestFailed) {
        // 保留现有 state（可能来自 SSR/上次成功），不覆盖、不闩锁。
        // 但预览参数必须仍然生效：后端冷启动/重启的瞬时不可达不该让后台
        // 「预览」按钮打开的新标签页静默退回当前激活主题。
        if (wantPreview && state.value.slug !== wantPreview) {
          state.value.slug = wantPreview
          state.value.previewing = true
          applyThemeColorTokens(state.value.mods)
          applyThemeVisual(state.value.slug, state.value.version)
        }
        return state.value
      }

      if (data && typeof data === 'object') {
        state.value.slug = typeof data.slug === 'string' ? data.slug : null
        state.value.name = typeof data.name === 'string' ? data.name : null
        state.value.version = typeof data.version === 'string' ? data.version : null
        state.value.screenshot_urls = normalizeScreenshotUrls(
          state.value.slug,
          Array.isArray(data.screenshot_urls) ? data.screenshot_urls : []
        )
        state.value.mods = mergeMods(data.mods)
        state.value.mods_schema
          = data.mods_schema && typeof data.mods_schema === 'object' && !Array.isArray(data.mods_schema)
            ? (data.mods_schema as JsonObject)
            : null
        state.value.tags = Array.isArray(data.tags)
          ? data.tags.filter((t: unknown) => typeof t === 'string')
          : []
      } else {
        // 【默认主题平级兜底 · 2026-09 解耦架构】
        // "无激活主题"不再让前台裸奔（slug=null）：直接回退加载内置默认主题
        // editorial-wp-style 的完整 CSS。前台任何时刻都恰好有一个完整主题在
        // 渲染路径上，不存在"先出中性骨架再补皮肤"的中间帧。
        // Admin 的「使用中」徽标读的是主题列表 API 的 is_active，不受此兜底影响。
        state.value.slug = DEFAULT_THEME_SLUG
        state.value.name = DEFAULT_THEME_NAME
        state.value.version = DEFAULT_THEME_VERSION
        state.value.screenshot_urls = []
        state.value.mods = { ...MODS_DEFAULTS }
        state.value.mods_schema = null
        state.value.tags = []
      }

      // 预览模式覆盖（解析在请求之前完成，见函数开头 wantPreview）
      if (wantPreview) {
        state.value.slug = wantPreview
        state.value.previewing = true
      } else {
        state.value.previewing = false
      }

      state.value.loaded = true
      // 本 app 已完成一次真实验证请求：同一客户端会话内后续 ensureLoaded 直接命中闩锁。
      _clientFetched.add(nuxtApp)
      applyThemeColorTokens(state.value.mods)
      applyThemeVisual(state.value.slug, state.value.version)
      return state.value
    })().finally(() => {
      if (_ensureInflight.get(nuxtApp) === task) _ensureInflight.delete(nuxtApp)
    })
    _ensureInflight.set(nuxtApp, task)
    return task
  }

  async function ensureLoaded(opts?: { force?: boolean }): Promise<FrontendThemeInfo> {
    if (state.value.loaded && !opts?.force) {
      if (import.meta.client && !_clientFetched.has(nuxtApp)) {
        // Hydrate 自 SWR 缓存页面的 loaded=true 不可信（缓存窗口内后台可能已换主题）。
        // 纠偏请求必须推迟到首帧挂载完成后（app:mounted）再发：本函数会被
        // 01-site-bootstrap 插件在 mount 之前 await，若 setup 期直接发请求，响应可能
        // 先于 Layout/Page 首帧渲染落地，把 isMinimalTheme 等模板分支翻到"新主题"，
        // 与服务端缓存的"旧主题"HTML 产生 Hydration mismatch。挂载完成后纠偏只是
        // 一次普通响应式更新，reactive state + useHead/applyThemeVisual 自动应用到 DOM。
        const fire = () => {
          _startFetch().catch(() => { /* 请求体内部已兜底 */ })
        }
        if (_appMounted.has(nuxtApp)) {
          fire()
        } else {
          nuxtApp.hook('app:mounted', () => {
            _appMounted.add(nuxtApp)
            fire()
          })
        }
      }
      return state.value
    }
    return _startFetch()
  }

  /**
   * 强制刷新内存 mods：重新拉取 /themes/active 并应用颜色 token 与视觉层。
   * 由后台 Customizer 保存 mods 后调用，保证全站立刻反映主题自定义。
   */
  async function reload() {
    try {
      await ensureLoaded({ force: true })
    } catch {
      /* ensureLoaded 内部兜底；这里永远不向外抛异常 */
    }
  }

  return {
    state,
    mods,
    isActive,
    slug,
    name,
    tags,
    isMinimal,
    override,
    showSidebar,
    sidebarPosition,
    postsPerRow,
    showAuthorBox,
    showRelatedPosts,
    showAvatar,
    previewing,
    ensureLoaded,
    reload,
    clearThemeVisual,
    applyThemeColorTokens: () => applyThemeColorTokens(state.value.mods),
    applyThemeVisual: (path?: string) =>
      applyThemeVisual(state.value.slug, state.value.version, path)
  }
}
