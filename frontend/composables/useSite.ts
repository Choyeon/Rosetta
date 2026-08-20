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
import { useSiteConfig } from '~~/composables/useCore'

type GroupKeys =
  | 'basic' | 'seo' | 'appearance' | 'hero' | 'footer'
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

function hexToHsl(hex: string): { h: number; s: number; l: number } | null {
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
      case r: h = (g - b) / d + (g < b ? 6 : 0); break
      case g: h = (b - r) / d + 2; break
      case b: h = (r - g) / d + 4; break
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

  const basic = computed(() => readGroup(state.value, 'basic', {
    site_name: (state.value.publicConfig?.site_name as string) || 'Rosetta',
    subtitle: (state.value.publicConfig?.site_subtitle as string) || 'Share knowledge, inspire creativity',
    description: (state.value.publicConfig?.site_description as string) ||
                 'Rosetta — A modern open-source multilingual blog.',
    keywords: (state.value.publicConfig?.site_keywords as string) || 'Rosetta,Blog,FastAPI,Nuxt',
    site_url: (state.value.publicConfig?.site_url as string) || '',
    logo: '',
    icp_number: '',
    about_content: ''
  }))

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
    return (value as Record<string, string>)[loc] ||
           (value as Record<string, string>).zh ||
           (value as Record<string, string>).en ||
           Object.values(value as Record<string, string>)[0] ||
           ''
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
          const { getSiteConfig } = useSiteConfig()
          const cfg = await getSiteConfig() as unknown as Record<string, unknown>
          state.value.publicConfig = cfg || null
        } catch { /* OOBE/offline */ }
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
