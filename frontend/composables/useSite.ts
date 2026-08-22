/**
 * useSite
 * --------
 * Frontend one-stop reader for admin-configurable site contents:
 *   - HTML <title> / hero headline / og:title —— from settings.basic / seo
 *   - theme primary & accent tokens          —— from settings.appearance
 *   - hero/footer/notice copy                —— hero/footer/notice groups
 *
 * Data source (matches backend 17 settings groups):
 *   GET /api/settings  (admin-only, may 401 for guests)
 *   GET /api/config    (public, fallback)
 */
import { computed } from 'vue'
import { fetchAllSettings } from '~~/composables/useAdminManage'
import { apiFetch } from '~~/composables/useApi'

/**
 * 与 GET /api/config 返回值完全一致的首屏默认值。
 * 关键原则：即使 SSR 或客户端首渲染前 apiFetch('/config') 偶发失败，
 * 两端使用同一份默认值，也能绝对保证 SSR HTML 与客户端 vdom 首渲染一致，
 * 从而避免 Hydration mismatch。真正的数据填充后会覆盖这些默认值。
 */
const PUBLIC_CONFIG_FALLBACK: Record<string, unknown> = {
  site_name: 'Rosetta Blog',
  site_subtitle: '',
  site_description: 'Rosetta开源博客系统',
  site_keywords: 'Rosetta, FastAPI, Astro, Svelte, Blog',
  site_url: '',
  site_logo: null,
  icp_number: null,
  about_content: '',
  about_page_html: '',
  footer_text: 'Powered by Rosetta',
  footer_slogan: 'Share knowledge, inspire creativity',
  copyright_text: null,
  footer_custom_html: '',
  theme_primary: '#0EA5A9',
  theme_accent: '#0284C7'
}

const mergePublic = (p: Record<string, unknown> | null | undefined): Record<string, unknown> => ({
  ...PUBLIC_CONFIG_FALLBACK,
  ...(p && typeof p === 'object' && !Array.isArray(p) ? p : {})
})

type GroupKeys
  = | 'basic' | 'seo' | 'appearance' | 'hero' | 'footer'
    | 'notice' | 'sidebar' | 'reading' | 'features'
    | 'friendlinks' | 'navigation' | 'media' | 'comments'
    | 'cache' | 'cdn' | 'email' | 'security'

interface UseSiteState {
  loaded: boolean
  groups: Partial<Record<GroupKeys, Record<string, unknown>>>
  publicConfig: Record<string, unknown> | null
}

const useStateRef = () =>
  useState<UseSiteState>('site:state', () => ({
    loaded: false,
    groups: {},
    publicConfig: null
  }))

function hexToHsl(hex: string): { h: number, s: number, l: number } | null {
  if (!hex) return null
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(String(hex).trim())
  if (!m) return null
  const r = parseInt(m[1] ?? '00', 16) / 255
  const g = parseInt(m[2] ?? '00', 16) / 255
  const b = parseInt(m[3] ?? '00', 16) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h = 0
  let s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: {
        h = (g - b) / d + (g < b ? 6 : 0)
        break
      }
      case g: {
        h = (b - r) / d + 2
        break
      }
      case b: {
        h = (r - g) / d + 4
        break
      }
    }
    h *= 60
  }
  return { h, s: s * 100, l: l * 100 }
}

function readGroup<T extends Record<string, unknown>>(
  state: UseSiteState,
  name: GroupKeys,
  fallback: T
): T {
  const val = state.groups[name] as T | undefined
  if (val && typeof val === 'object') return { ...fallback, ...val } as T
  return fallback
}

export function useSite() {
  const state = useStateRef()

  /**
   * 公开基础信息（site_name / subtitle / logo 等）：
   * —— 公开页面 & SSR 阶段一律走 publicConfig（来自 /api/config，匿名也能拿到），
   *    保证 SSR 输出 & 客户端首渲染值字节级一致。
   *
   * 为什么不能优先用 groups.basic？
   *   - groups.basic 来自 GET /api/settings（需要 admin 权限）
   *   - SSR 服务端是匿名请求，拿不到浏览器 cookie，groups 为空
   *   - 客户端已登录时能取到 groups.basic，site_name 可能是 "Rosetta Blog"
   *   - 结果 SSR HTML 里是 "Rosetta"，客户端 vdom 是 "Rosetta Blog" → mismatch
   *
   * 策略：
   *   - SSR（import.meta.server === true）：只用 publicConfig + 默认值（两端一致）
   *   - 公开页面客户端：只用 publicConfig + 默认值（和 SSR 一致，避免 Hydrate 前状态差）
   *   - 管理后台（ssr:false）：groups.basic 优先，publicConfig 兜底（表单编辑需要完整值）
   *
   *  —— 注意：所有 publicConfig 派生值必须写在 computed 内部，否则 useSite() 首次调用
   *    时 publicConfig 还未被 ensureLoaded() 异步填充，就永远固化成 fallback 了。
   */
  const basic = computed(() => {
    const p = mergePublic(state.value.publicConfig)
    const publicName = (p.site_name as string) || 'Rosetta Blog'
    const publicSubtitle = (p.site_subtitle as string) || (p.footer_slogan as string) || 'Share knowledge, inspire creativity'
    const publicDesc = (p.site_description as string) || 'Rosetta开源博客系统'
    const publicKw = (p.site_keywords as string) || 'Rosetta, FastAPI, Astro, Svelte, Blog'
    const publicUrl = (p.site_url as string) || ''
    const publicLogo = (p.site_logo as string) || ''
    const publicIcp = (p.icp_number as string) || ''
    const publicAbout = (p.about_content as string) || ''
    // 关于页完整 HTML 内容：admin 在 basic.about_page_html 字段里用 HTML 方式直接编辑
    // 前台 /about 页面若此字段非空，直接 v-html 渲染；为空时展示 about.vue 默认 Tab 结构
    const publicAboutHtml = (p.about_page_html as string) || ''
    return {
      site_name: publicName,
      subtitle: publicSubtitle,
      description: publicDesc,
      keywords: publicKw,
      site_url: publicUrl,
      logo: publicLogo,
      icp_number: publicIcp,
      about_content: publicAbout,
      about_page_html: publicAboutHtml
    }
  })

  const seo = computed(() => readGroup(state.value, 'seo', {
    default_title: basic.value.subtitle,
    default_description: basic.value.description,
    default_keywords: basic.value.keywords,
    og_image: (state.value.publicConfig?.default_og_image as string) || '',
    twitter_handle: '',
    google_analytics_id: '',
    baidu_analytics_id: '',
    google_verification: '',
    baidu_verification: '',
    robots_txt: 'User-agent: *\nAllow: /'
  }))

  const appearance = computed(() => readGroup(state.value, 'appearance', {
    code_theme: 'github',
    code_theme_dark: 'github-dark',
    default_theme: 'system',
    primary_color: (state.value.publicConfig?.theme_primary as string) || '#0EA5A9',
    accent_color: (state.value.publicConfig?.theme_accent as string) || '#0284C7',
    font_family: '',
    page_width_px: 1200,
    show_copyright: true,
    show_powered_by: true
  }))

  const hero = computed(() => readGroup(state.value, 'hero', {
    enable: true,
    title: { zh: basic.value.site_name, en: basic.value.site_name },
    subtitle: { zh: basic.value.subtitle, en: basic.value.subtitle },
    caption: '',
    cta_text: { zh: '开始阅读', en: 'Start Reading' },
    cta_url: '/posts',
    bg_image: '',
    bg_gradient: ''
  }))

  const footer = computed(() => readGroup(state.value, 'footer', {
    text: basic.value.subtitle,
    slogan: basic.value.subtitle,
    copyright: `© ${new Date().getFullYear()} ${basic.value.site_name}`,
    icp_number: basic.value.icp_number,
    police_icp_number: '',
    show_social_links: true,
    show_back_to_top: true
  }))

  const siteTitle = computed(() => basic.value.site_name)
  const siteSubtitle = computed(() => basic.value.subtitle || seo.value.default_title)
  const siteDescription = computed(() => seo.value.default_description || basic.value.description)
  const siteKeywords = computed(() => seo.value.default_keywords || basic.value.keywords)

  const withSuffix = (pageTitle?: string | null): string => {
    const name = siteTitle.value || 'Rosetta'
    const sub = siteSubtitle.value || ''
    if (pageTitle && String(pageTitle).trim()) {
      return `${String(pageTitle).trim()} · ${name}`
    }
    if (sub) return `${name} · ${sub}`
    return name
  }

  const pickI18n = (
    value: string | Record<string, string> | undefined,
    locale?: string
  ): string => {
    const { locale: cur } = useI18n()
    const loc = locale || cur.value
    if (value == null) return ''
    if (typeof value === 'string') return value
    if (typeof value !== 'object') return ''
    return (value as Record<string, string>)[loc]
      || (value as Record<string, string>).zh
      || (value as Record<string, string>).en
      || Object.values(value as Record<string, string>)[0]
      || ''
  }

  const applyAppearanceTokens = () => {
    if (!import.meta.client) return
    const root = document.documentElement
    const { primary_color, accent_color } = appearance.value

    const accent = hexToHsl(String(accent_color || '#0284C7'))
    if (accent) {
      root.style.setProperty('--theme-accent-hue', String(Math.round(accent.h)))
      root.style.setProperty('--theme-accent-sat', `${Math.round(accent.s)}%`)
      root.style.setProperty('--theme-accent-light', `${Math.round(accent.l)}%`)
    }

    const primary = hexToHsl(String(primary_color || '#0EA5A9'))
    if (primary) {
      root.style.setProperty('--primary', `${Math.round(primary.h)} ${Math.round(primary.s)}% ${Math.round(primary.l)}%`)
      const ringL = Math.min(96, primary.l * 1.12)
      root.style.setProperty('--ring', `${Math.round(primary.h)} ${Math.round(primary.s + 2)}% ${ringL}%`)
    }
  }

  const ensureLoaded = async (opts?: { force?: boolean }): Promise<UseSiteState> => {
    if (state.value.loaded && !opts?.force) return state.value

    await Promise.all([
      (async () => {
        try {
          // 注意：这里必须用 apiFetch（Promise<T>），不能用 useAPI / useFetch 返回的
          // AsyncData 对象——后者包含 .refresh / execute 等函数，塞到 payload state
          // 里会让 devalue 抛出 "Cannot stringify a function"，导致 / 路由 500。
          const cfg = await apiFetch<Record<string, unknown>>('/config', { method: 'GET' })
          state.value.publicConfig = cfg && typeof cfg === 'object' && !Array.isArray(cfg)
            ? (cfg as Record<string, unknown>)
            : null
        } catch { /* OOBE / backend unreachable → use defaults */ }
      })(),
      (async () => {
        try {
          const groups = await fetchAllSettings()
          if (groups && typeof groups === 'object') {
            state.value.groups = groups as UseSiteState['groups']
          }
        } catch { /* guest/401, fall back to publicConfig */ }
      })()
    ])

    state.value.loaded = true
    applyAppearanceTokens()
    return state.value
  }

  return {
    state,
    basic,
    seo,
    appearance,
    hero,
    footer,
    siteTitle,
    siteSubtitle,
    siteDescription,
    siteKeywords,
    withSuffix,
    pickI18n,
    applyAppearanceTokens,
    ensureLoaded
  }
}
