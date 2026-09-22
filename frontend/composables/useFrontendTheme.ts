/**
 * useFrontendTheme
 * -----------------
 * 读取当前公开启用的 Rosetta 主题（GET /api/themes/active），把它的 mods / slug / schema
 * 以 SSR-safe 的 useState 形式暴露给全站。
 *
 * 主题 mods 覆盖规则（与 settings 去重后的最终落地）：
 *   - 主色 / 强调色 / 内容区宽度：theme 若定义则覆盖 settings.appearance
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
import { KNOWN_ROSETTA_THEMES } from '~~/lib/rosetta-themes'

type JsonObject = Record<string, unknown>

export interface FrontendThemeInfo {
  slug: string | null
  name: string | null
  version: string | null
  screenshot_urls: string[]
  mods: ThemeModsRuntime
  mods_schema: JsonObject | null
  loaded: boolean
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
  posts_per_row: 2 | 3 | 4
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

const useThemeState = () =>
  useState<FrontendThemeInfo>('frontend-theme:state', () => ({
    slug: null,
    name: null,
    version: null,
    screenshot_urls: [],
    mods: { ...MODS_DEFAULTS },
    mods_schema: null,
    loaded: false,
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
        const n = Number(v)
        if (!Number.isNaN(n) && n >= 640 && n <= 1600) out.layout_width = Math.round(n)
        break
      }
      case 'posts_per_row': {
        const n = Number(v)
        if (n === 2 || n === 3 || n === 4) out.posts_per_row = n as 2 | 3 | 4
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
      default:
        if (v !== undefined) out[k] = v
        break
    }
  }
  return out
}

/**
 * 把主题 accent_color / primary_color 写进 :root 样式变量。
 * 优先顺序：theme mods > settings.appearance 的 applyAppearanceTokens。
 * 这里只覆盖主题里显式给了颜色的变量，空字符串留给 settings 兜底。
 *
 * 【SSR 策略】
 * 注意：ensureLoaded() 里调用 apply* 发生在 `await apiFetch(...)` 之后——而 Nuxt SSR
 * 的 async setup 在"第一个 await 之后"会**丢失同步 NuxtApp 上下文**，在那之后再调
 * useHead() 会触发 NUXT_E1001。因此 SSR 端的颜色 token / 视觉层注入不在本函数里做，
 * 而是在 useFrontendTheme() 首次创建时（同步阶段、上下文有效）注册一个
 * `useHead(() => reactiveCallback)`，后续 ensureLoaded 改写的 state.value.mods/slug
 * 会被 Unhead 响应式追踪自动刷新，全程无需再次调用 useHead。
 *
 * 客户端分支：沿用历史 DOM 直接写，避免 useHead 的 <style> 与客户端对同一个变量
 * 的多次修改互相覆盖（DOM style.setProperty 优先级最高，是最终值）。
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
  if (mods.primary_color) {
    const hsl = hexToHsl(mods.primary_color)
    if (hsl) {
      root.style.setProperty(
        '--primary',
        `${Math.round(hsl.h)} ${Math.round(hsl.s)}% ${Math.round(hsl.l)}%`
      )
      const ringL = Math.min(96, hsl.l * 1.12)
      root.style.setProperty(
        '--ring',
        `${Math.round(hsl.h)} ${Math.round(hsl.s + 2)}% ${ringL}%`
      )
    }
  }
}

/**
 * 永不可应用主题视觉层的路径（后台 / OOBE 向导）——避免 theme CSS 泄漏进 Admin。
 *
 * 2026-09 调整：/login 与 /register 从排除名单移出。它们的 data-layout-scope
 * 是 "public-auth"（而非 "frontend"），主题 style.css 的既有规则全部带
 * [data-layout-scope="frontend"] 守卫、在认证页上不命中；因此这里允许注入
 * slug 属性 + <link>，供主题 CSS 中显式书写的 public-auth 段落（极简登录/
 * 注册页、toast 统一）消费，零耦合约束依旧成立。
 */
const FRONTEND_EXCLUDE_PREFIXES = ['/admin', '/oobe']

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
  if (!p) return false
  return FRONTEND_EXCLUDE_PREFIXES.some(prefix => p!.startsWith(prefix))
}

/**
 * 已知 Rosetta 主题 slug 集合（~~/lib/rosetta-themes 单一权威来源），
 * 用于判定 data-theme 是否由我们写入、可否在 admin 清理时移除。
 */

/**
 * 所有曾注入过的主题 style.css <link> 注册表（slug → HTMLLinkElement）。
 * 共享给 _clearThemeVisual（admin 清理）与 applyThemeVisual（前台加载/切换）两边共同使用。
 * 【声明位置必须在 _clearThemeVisual 之前，避免 TDZ 错误】
 */
const _INSTALLED_LINKS = new Map<string, HTMLLinkElement>()

/**
 * 彻底清理 <html> 上的 Rosetta 主题视觉痕迹：
 *   · theme-* class
 *   · data-rosetta-theme / data-theme（仅当值为已知主题 slug 时才移除，避免破坏明暗主题的 light/dark）
 *   · 已注入的 /themes/<slug>/style.css <link>
 *   · --theme-accent-* / --primary / --ring 覆盖变量
 *
 * 此函数 idempotent，admin 布局 onMounted / 路由切换时主动调用，保证后台永远是
 * shadcn 原生样式，不被前端主题 CSS 误伤。
 */
function _clearThemeVisual() {
  if (!import.meta.client) return
  const root = document.documentElement

  // 1) 清理 class
  for (const cls of Array.from(root.classList)) {
    if (cls.startsWith('theme-')) root.classList.remove(cls)
  }

  // 2) 清理 data-* 属性
  root.removeAttribute('data-rosetta-theme')
  const currentDT = root.getAttribute('data-theme')
  if (currentDT && KNOWN_ROSETTA_THEMES.has(currentDT)) {
    root.removeAttribute('data-theme')
  }

  // 3) 清理 <link>（Map 里保留所有曾安装的 link，彻底移除防止 admin 页残留）
  for (const [k, el] of _INSTALLED_LINKS) {
    el.remove()
    _INSTALLED_LINKS.delete(k)
  }

  // 4) 清理颜色 token（避免 accent/primary 污染 admin 原生配色）
  root.style.removeProperty('--theme-accent-hue')
  root.style.removeProperty('--theme-accent-sat')
  root.style.removeProperty('--theme-accent-light')
  // 注意：--primary / --ring 不直接删，它们由 settings.appearance 与 shadcn 共同管理，
  //      主题层只在 applyThemeColorTokens 中做"写入覆盖"，后续调用 applyThemeColorTokens({...空默认值})
  //      不会清除——这里用"重设为空字符串让 CSS 走 fallback"的方式。
  if (root.style.getPropertyValue('--primary').includes('calc') === false) {
    root.style.removeProperty('--primary')
    root.style.removeProperty('--ring')
  }
}

/**
 * manifest.scrennshot_urls 允许三种写法：
 *   1) 相对文件名：screenshot.png → 补齐 /themes/{slug}/screenshot.png
 *   2) 根路径相对：/xxx.png → 直接使用（前端 public 资源或其它已挂载路径）
 *   3) 绝对 URL：https://... → 直接使用（外链 CDN/OSS 场景）
 */
function normalizeScreenshotUrls(slug: string | null, raws: unknown): string[] {
  if (!Array.isArray(raws)) return []
  const out: string[] = []
  for (const r of raws) {
    if (typeof r !== 'string' || !r) continue
    if (/^https?:\/\//i.test(r) || r.startsWith('/')) {
      out.push(r)
    } else if (slug) {
      out.push(`/themes/${slug}/${r}`)
    }
  }
  return out
}
function applyThemeVisual(slug: string | null, explicitPath?: string) {
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
  for (const cls of Array.from(root.classList)) {
    if (cls.startsWith('theme-')) root.classList.remove(cls)
  }
  root.removeAttribute('data-rosetta-theme')
  const currentDataTheme = root.getAttribute('data-theme')
  if (currentDataTheme && KNOWN_ROSETTA_THEMES.has(currentDataTheme)) {
    root.removeAttribute('data-theme')
  }
  for (const [k, el] of _INSTALLED_LINKS) {
    if (k !== slug) {
      el.remove()
      _INSTALLED_LINKS.delete(k)
    }
  }

  // 2) 去激活（没有 slug）→ 到此结束（上方已做清理）
  if (!slug) return

  // 3) 应用新 slug
  root.classList.add(`theme-${slug}`)
  root.setAttribute('data-rosetta-theme', slug)
  // 兼容 style.css 里广泛使用的 [data-theme="<slug>"] 前缀选择器。
  // 不覆盖明暗模式占用的 light/dark 值。
  const existingDT = root.getAttribute('data-theme')
  if (!existingDT || KNOWN_ROSETTA_THEMES.has(existingDT) || existingDT === slug) {
    root.setAttribute('data-theme', slug)
  }

  if (_INSTALLED_LINKS.has(slug)) return
  // 主题 <link> 有两个潜在来源：
  //   · useHead 响应式注入（SSR 首字节 / 客户端 slug 变化后由 unhead 批量 flush，
  //     其时机可能晚于宏任务，不能用一次同步检查判定）
  //   · 本函数的 DOM 直接注入（ssr:false 认证页 / error 页等纯客户端路径的兜底）
  // 策略：先认领已存在的 unhead 节点；没有则创建带 data-rosetta-manual 标记的兜底
  // 节点，并在 unhead 通常已 flush 完成后移交——若其 id 节点出现，移除兜底、认领正主。
  const MANUAL_ATTR = 'data-rosetta-manual'
  const install = () => {
    if (_INSTALLED_LINKS.has(slug)) return
    const existing = document.querySelector<HTMLLinkElement>(
      `link[rel="stylesheet"][href="/themes/${slug}/style.css"]`
    )
    if (existing) {
      _INSTALLED_LINKS.set(slug, existing)
      return
    }
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = `/themes/${slug}/style.css`
    link.setAttribute(MANUAL_ATTR, '1')
    link.onerror = () => {
      link.remove()
      _INSTALLED_LINKS.delete(slug)
    }
    document.head.appendChild(link)
    _INSTALLED_LINKS.set(slug, link)
    // 移交：unhead 的响应式节点到位后，移除手动兜底，避免同一 style.css 双 <link>
    setTimeout(() => {
      const mine = _INSTALLED_LINKS.get(slug)
      if (!mine || !mine.hasAttribute(MANUAL_ATTR)) return
      const headLink = document.querySelector<HTMLLinkElement>(
        `link[id="rosetta-theme-css-${slug}"]`
      )
      if (headLink && headLink !== mine) {
        mine.remove()
        _INSTALLED_LINKS.set(slug, headLink)
      }
    }, 400)
  }
  install()
}

/**
 * 对外暴露的清理入口：由 admin.vue / login.vue 等非前台布局调用，
 * 保证进入这些路由时 html 永远不保留 Rosetta 主题的视觉钩子。
 */
function clearThemeVisual() {
  _clearThemeVisual()
}

export function useFrontendTheme() {
  const state = useThemeState()
  const route = useRoute()

  // =========================================================================
  // 【SSR 核心：同步阶段注册 reactive useHead】
  // 永远不要把 useHead() 放在 ensureLoaded() 的 await apiFetch(...) 之后调用——
  // Nuxt SSR async setup 在"第一个 await 之后"会丢失同步 NuxtApp 上下文，
  // 在此之后调 useHead 会触发 NUXT_E1001，子组件 VNode 会被渲染为 undefined。
  //
  // 解决方案：在 composable 创建时（同步阶段、上下文仍有效）注册一次
  // useHead(() => reactiveCallback)。后续 ensureLoaded 改写 state.value 的
  // slug / mods 变化都会被 Unhead 自动追踪并响应式刷新 head / htmlAttrs，
  // 首字节 HTML 即包含主题四件套 + 颜色 tokens，全程零 E1001。
  // =========================================================================
  useHead(() => {
    const s = state.value
    const excluded = FRONTEND_EXCLUDE_PREFIXES.some(prefix => route.path.startsWith(prefix))

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
          href: `/themes/${s.slug}/style.css`,
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
      // primary → --primary / --ring
      if (s.mods.primary_color) {
        const hsl = hexToHsl(s.mods.primary_color)
        if (hsl) {
          styleTokens.push(
            `--primary:${Math.round(hsl.h)} ${Math.round(hsl.s)}% ${Math.round(hsl.l)}%`
          )
          const ringL = Math.min(96, hsl.l * 1.12)
          styleTokens.push(`--ring:${Math.round(hsl.h)} ${Math.round(hsl.s + 2)}% ${ringL}%`)
        }
      }
    }

    type StyleItem = { id: 'rosetta-theme-color-tokens', innerHTML: string }
    const style: StyleItem[] = styleTokens.length
      ? [{ id: 'rosetta-theme-color-tokens', innerHTML: `:root{${styleTokens.join(';')}}` }]
      : []

    return { htmlAttrs, link, style }
  })

  const mods = computed<ThemeModsRuntime>(() => state.value.mods)
  const isActive = computed(() => !!state.value.slug)
  const slug = computed(() => state.value.slug)
  const name = computed(() => state.value.name)

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

  async function ensureLoaded(opts?: { force?: boolean }) {
    if (state.value.loaded && !opts?.force) return state.value
    let data: JsonObject | null = null
    type ThemeActiveResp = { success: boolean, data: JsonObject | null }
    try {
      const resp = await apiFetch<ThemeActiveResp>('/themes/active', {
        method: 'GET',
        silentToast: true
      })
      data
        = resp && typeof resp === 'object' && (resp as ThemeActiveResp).success
          ? ((resp as ThemeActiveResp).data as JsonObject | null) ?? null
          : null
    } catch {
      /* 404 / 未启用主题 / 后端不可达 → 保持默认值 */
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
    } else {
      state.value.slug = null
      state.value.name = null
      state.value.version = null
      state.value.screenshot_urls = []
      state.value.mods = { ...MODS_DEFAULTS }
      state.value.mods_schema = null
    }

    // ── 预览模式：?rosetta_theme_preview=<slug> ──────────────────────────
    // 由后台「主题管理」的预览按钮打开新标签页触发。仅允许 KNOWN_ROSETTA_THEMES
    // 白名单内的 slug，覆盖 state.slug 以挂载该主题的 style.css + htmlAttrs，
    // 但不改动后端 active 主题。mods 沿用 active 主题（或默认值）——内建主题的
    // 视觉差异主要在 style.css，slug 覆盖即可得到忠实预览。
    // 读取 route.query 是对已捕获 reactive 对象的属性访问，await 之后仍安全。
    const previewRaw = route.query.rosetta_theme_preview
    const previewSlug = Array.isArray(previewRaw) ? previewRaw[0] : previewRaw
    if (typeof previewSlug === 'string' && KNOWN_ROSETTA_THEMES.has(previewSlug)) {
      state.value.slug = previewSlug
      state.value.previewing = true
    } else {
      state.value.previewing = false
    }

    state.value.loaded = true
    applyThemeColorTokens(state.value.mods)
    applyThemeVisual(state.value.slug)
    return state.value
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
    applyThemeVisual: (path?: string) => applyThemeVisual(state.value.slug, path)
  }
}
