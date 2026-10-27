/**
 * useSite
 * --------
 * Frontend one-stop reader for admin-configurable site contents:
 *   - HTML <title> / hero headline / og:title —— from settings.basic / seo
 *   - theme primary & accent tokens          —— from settings.appearance
 *   - hero/footer/notice copy                —— hero/footer/notice groups
 *
 * Data source (matches backend 14 settings groups):
 *   GET /api/settings/public  (无鉴权；脱敏后的公开子集：basic/appearance/hero/footer/seo/notice/navigation/reading/features/donate/comments)
 *   GET /api/config           (公开兜底同步 fallback)
 */
import { computed, getCurrentInstance } from 'vue'
import type { AllSettingsGroups } from '~~/composables/useAdminManage'
import { apiFetch } from '~~/composables/useApi'
import { hexToHsl } from '~~/lib/utils'

/**
 * 组件实例之外求值的 computed 里不能直接 useI18n()：unhead 在 SSR 收尾期解析
 * useSeo() 收进去的 Ref，watch 回调里的第一次求值同样没有组件实例，这两种情况下
 * vue-i18n 抛 code 26（MUST_BE_CALL_SETUP_TOP）= 整页 500（实测 /sponsor 全语言）。
 * 所以优先用实例内 composer，拿不到就回落到 Nuxt 注入的全局 composer，最后返回空串
 * （空串让 pickI18n 走 dict 自带的 zh/en 兜底，而不是把访客页打成错误页）。
 */
function safeI18n(): { t: (key: string) => string, locale: string } {
  if (getCurrentInstance()) {
    try {
      const c = useI18n()
      return { t: (key: string) => String(c.t(key)), locale: String(c.locale.value) }
    } catch {
      // 实例存在但 composer 不可用（极端挂载时序）：继续走全局回落分支
    }
  }
  try {
    const g = useNuxtApp().$i18n as { locale?: unknown, t?: (key: string) => unknown } | undefined
    const raw = g?.locale
    const locale = typeof raw === 'string' ? raw : String((raw as { value?: unknown })?.value ?? '')
    return { t: (key: string) => String(g?.t?.(key) ?? ''), locale }
  } catch {
    return { t: () => '', locale: '' }
  }
}

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
    | 'notice' | 'reading' | 'features'
    | 'navigation' | 'media' | 'comments'
    | 'email' | 'security' | 'donate'

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
  const theme = useFrontendTheme()
  const themeOverrides = theme.override

  /**
   * 公开基础信息（site_name / subtitle / logo 等）：
   * —— 公开页面 & SSR 阶段一律走 publicConfig（来自 /api/config，匿名也能拿到），
   *    保证 SSR 输出 & 客户端首渲染值字节级一致。
   *
   * 为什么 layout 的 basic 不优先用 groups.basic？
   *   - SSR 服务端是匿名请求，拿不到浏览器 cookie/localStorage 中的 token
   *   - 若 SSR 端读得到而客户端读不到（或反之），两端 site_name 不一致 → Hydration mismatch
   *   - /api/config 是公开接口，SSR 与客户端拿到完全一致的同一份值，因此它才是唯一权威来源
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
      about_page_html: publicAboutHtml
    }
  })

  const seo = computed(() => readGroup(state.value, 'seo', {
    default_title: basic.value.subtitle,
    default_description: basic.value.description,
    default_keywords: basic.value.keywords,
    og_image: (state.value.publicConfig?.default_og_image as string) || '',
    twitter_handle: '',
    google_verification: '',
    baidu_verification: '',
    robots_txt: 'User-agent: *\nAllow: /'
  }))

  const appearance = computed(() => {
    const base = readGroup(state.value, 'appearance', {
      primary_color: (state.value.publicConfig?.theme_primary as string) || '#0EA5A9',
      accent_color: (state.value.publicConfig?.theme_accent as string) || '#0284C7',
      page_width_px: 1200,
      show_copyright: true,
      show_powered_by: true
    })
    // ====== 主题 Customizer 去重覆盖 ======
    // 主色 / 强调色 / 内容区宽度：若当前激活主题在 mods 里显式配置，则优先生效。
    // 对应站点设置页面里的"外观主题"组已移除这三项（避免双入口冲突）。
    if (themeOverrides.primary_color.value) base.primary_color = themeOverrides.primary_color.value
    if (themeOverrides.accent_color.value) base.accent_color = themeOverrides.accent_color.value
    if (themeOverrides.layout_width.value != null) base.page_width_px = themeOverrides.layout_width.value
    return base
  })

  const hero = computed(() => {
    // Hero 文案优先级：
    //   1) settings.hero.* (管理员手动在后台配置，多语言 i18n dict)
    //   2) theme mods：hero_title / hero_subtitle（主题 Customizer，纯字符串 → 被写成多语言副本）
    //   3) i18n home.heroTitle / home.heroSubtitle（四种语言都有，兜底不会出现 site_name 当大标题）
    const { t, locale } = safeI18n()
    const fallbackTitle = {
      zh: String(t('home.heroTitle') || '代码、文字、光与影'),
      en: String(t('home.heroTitle') || 'Write. Think. Settle.'),
      ja: String(t('home.heroTitle') || 'コードと思考の記録'),
      zh_Hant: String(t('home.heroTitle') || '程式碼與思考的足跡')
    }
    const fallbackSubtitle = {
      zh: String(t('home.heroSubtitle') || basic.value.subtitle || '互联网上的一个私人角落：工程笔记、阅读心得、日常生活切片。用心书写，耐心阅读。'),
      en: String(t('home.heroSubtitle') || basic.value.subtitle || 'A minimal blog for engineers and creators.'),
      ja: String(t('home.heroSubtitle') || basic.value.subtitle || '個人の技術ブログへようこそ。'),
      zh_Hant: String(t('home.heroSubtitle') || basic.value.subtitle || '歡迎來到我的個人技術部落格。')
    }
    const base = readGroup(state.value, 'hero', {
      enable: true,
      title: fallbackTitle as Record<string, string>,
      subtitle: fallbackSubtitle as Record<string, string>,
      caption: '',
      cta_text: {
        zh: String(t('home.startReading') || '开始阅读'),
        en: 'Start Reading',
        ja: '読書開始',
        zh_Hant: '開始閱讀'
      } as Record<string, string>,
      cta_url: '/posts',
      bg_image: '',
      bg_gradient: ''
    })
    // ====== 主题 Customizer 去重覆盖 ======
    if (themeOverrides.hero_title.value) {
      const v = String(themeOverrides.hero_title.value)
      base.title = { zh: v, en: v, ja: v, zh_Hant: v } as Record<string, string>
    } else if (!base.title || typeof base.title !== 'object' || !String(base.title[locale] || base.title.zh || '').trim()) {
      base.title = fallbackTitle as Record<string, string>
    }
    if (themeOverrides.hero_subtitle.value) {
      const v = String(themeOverrides.hero_subtitle.value)
      base.subtitle = { zh: v, en: v, ja: v, zh_Hant: v } as Record<string, string>
    } else if (!base.subtitle || typeof base.subtitle !== 'object' || !String(base.subtitle[locale] || base.subtitle.zh || '').trim()) {
      base.subtitle = fallbackSubtitle as Record<string, string>
    }
    return base
  })

  const footer = computed(() => {
    const base = readGroup(state.value, 'footer', {
      // text 是页脚 Powered by 那一行的可选覆写，兜底必须留空：这一行有内置四语文案
      // （i18n footer.poweredBy），用副标题播种会让它永远非空、覆写形同虚设。
      text: '',
      slogan: basic.value.subtitle,
      copyright: `© ${new Date().getFullYear()} ${basic.value.site_name}`,
      icp_number: basic.value.icp_number,
      police_icp_number: '',
      show_social_links: true,
      show_back_to_top: true
    })
    // ====== 主题 Customizer 去重覆盖 ======
    // 主题 mods.footer_text 若定义 → 直接覆盖 settings 的 copyright 文案（设置页里"页脚"
    // 组的版权字段已隐藏，避免双入口冲突）。
    if (themeOverrides.footer_text.value) base.copyright = themeOverrides.footer_text.value
    return base
  })

  /**
   * 「站点公告」分组（设置页 notice 组，后端 _default_notice 同构）。
   * 读侧唯一消费者是 layouts/default.vue 的公告条——此前这个分组能存能读却没人渲染，
   * 属于"后台配了前台不生效"的死配置；口径见 composables/useAnnouncementBar.ts 的 noticeToRow。
   */
  const notice = computed(() => readGroup(state.value, 'notice', {
    enable: false,
    type: 'info',
    title: '',
    content_md: '',
    dismissible: true,
    sticky: true
  }))

  /**
   * 「阅读体验」分组（后端 _default_reading 同构）。
   * 此前这 7 个键只进库不进制：列表每页条数、目录/字数/阅读时间三处 UI 全部硬编码。
   * 兜底值取**改动前各页面实际使用的那组数**，保证未保存过分组的站点渲染结果不变。
   */
  const reading = computed(() => {
    const g = readGroup(state.value, 'reading', {} as Record<string, unknown>)
    const pos = (k: string, d: number) => {
      const n = Number(g[k])
      return Number.isFinite(n) && n > 0 ? n : d
    }
    const flag = (k: string) => g[k] !== false
    return {
      // 与后端 _default_reading.posts_per_page 同值（9 = 三列网格 × 3 行，也是接这个设置
      // 之前各列表页写死的条数）。后端默认值曾写 12，而 /settings/public 下发的是
      // "默认值 + 存值"合并后的整组，于是这个 9 只在接口失败时才生效——同一个设置两套版式。
      posts_per_page: pos('posts_per_page', 9),
      show_reading_time: flag('show_reading_time'),
      show_word_count: flag('show_word_count'),
      show_toc: flag('show_toc'),
      toc_depth: pos('toc_depth', 3),
      line_height: pos('line_height', 1.7),
      font_size: pos('font_size', 16)
    }
  })

  /**
   * 「功能开关」分组。后端把同一份值叠进 /api/config（core.py::_apply_settings_groups），
   * 评论写口与 RSS/sitemap 的服务端闸门在后端，这里只负责"后台关了前台就别再显示入口"。
   * enable_comments 不在这里：评论的唯一开关是 comments.enable（后端写口闸门读的就是它），
   * 这里再暴露一份等于给管理员两个各管一半的按钮。
   */
  const features = computed(() => {
    const g = readGroup(state.value, 'features', {} as Record<string, unknown>)
    const flag = (k: string, d = true) => (typeof g[k] === 'boolean' ? g[k] : d)
    return {
      enable_registration: flag('enable_registration'),
      enable_rss: flag('enable_rss'),
      enable_search: flag('enable_search'),
      enable_sitemap: flag('enable_sitemap'),
      enable_guestbook: flag('enable_guestbook'),
      enable_dark_mode: flag('enable_dark_mode'),
      enable_like_button: flag('enable_like_button'),
      enable_share_buttons: flag('enable_share_buttons'),
      enable_reading_progress: flag('enable_reading_progress'),
      // 默认关：老站点没勾过这一项，评论/留言必须保持"无需验证码也能发"。
      enable_captcha: flag('enable_captcha', false)
    }
  })

  /**
   * 「评论」分组（后端 _default_comments 同构）。
   * 兜底值取**后端 _default_comments 的同一组数**（未保存过分组时两边必须同一口径，
   * 否则后台「允许访客匿名评论」勾着而前台仍要登录＝又一个看起来失效的开关）。
   * enable 也在这里：它就是评论功能的唯一开关——后端写口（CommentService 的
   * COMMENTS_DISABLED）与前台评论区/表单（pages/posts/[slug].vue）读的都是这一项。
   */
  const comments = computed(() => {
    const g = readGroup(state.value, 'comments', {} as Record<string, unknown>)
    const flag = (k: string, d: boolean) => (typeof g[k] === 'boolean' ? g[k] : d)
    const n = Number(g.max_length)
    return {
      enable: flag('enable', true),
      allow_guest: flag('allow_guest', true),
      enable_nested: flag('enable_nested', true),
      require_approval: flag('require_approval', false),
      max_length: Number.isFinite(n) && n > 0 ? n : 3000
    }
  })

  /**
   * 「导航」分组。顶栏三个入口开关与吸顶样式由 AppHeader 消费；
   * 与 features 分组的同义项（enable_search / enable_dark_mode）是"与"关系：
   * features 决定这个功能在这个站点是否**存在**，navigation 决定顶栏是否**放入口**。
   * 注：custom_links（自定义链接）已删除——它从未被顶栏读取，导航条的唯一清单是
   * 后台「导航菜单」页面的导航项 CRUD（/api/navigations）。
   */
  const navigation = computed(() => readGroup(state.value, 'navigation', {
    header_style: 'sticky',
    show_search: true,
    show_language_switch: true,
    show_theme_toggle: true
  }))

  const siteTitle = computed(() => basic.value.site_name)
  // seo.default_title（后台「SEO」里的"页面默认标题"）优先：basic.subtitle 永远非空
  // （下面这条兜底链最后一个是写死的英文标语），把 default_title 放在后面等于
  // 给管理员一个填了也永远不会被读到的输入框。留空时仍回落到站点副标题。
  const siteSubtitle = computed(() => seo.value.default_title || basic.value.subtitle)
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
    const { locale: cur } = safeI18n()
    const loc = locale || cur
    if (value == null) return ''
    if (typeof value === 'string') return value
    if (typeof value !== 'object') return ''
    return (value as Record<string, string>)[loc]
      || (value as Record<string, string>).zh
      || (value as Record<string, string>).en
      || Object.values(value as Record<string, string>)[0]
      || ''
  }

  /**
   * 「捐助」分组：/sponsor 页的唯一内容源。
   * methods 每项 {name,image,note}；名称与图片都为空的行不渲染（后台保存时已剥离，
   * 这里再挡一次存量脏数据）。
   * sponsors 是打赏墙名单，每项 {name,avatar,amount,date}；show_sponsors_list 关掉
   * 或名单为空时整块不渲染（后端 GET /api/sponsors 读同一份值、同一口径回空）。
   */
  const donate = computed(() => {
    const g = readGroup(state.value, 'donate', {
      enable: true,
      title: {} as Record<string, string>,
      description: {} as Record<string, string>,
      methods: [] as unknown[],
      sponsors: [] as unknown[],
      show_sponsors_list: true
    })
    const methods = (Array.isArray(g.methods) ? g.methods : [])
      .map((raw): { name: string, image: string, note: string } => {
        const item = (raw ?? {}) as Record<string, unknown>
        return {
          name: typeof item.name === 'string' ? item.name : '',
          image: typeof item.image === 'string' ? item.image : '',
          note: typeof item.note === 'string' ? item.note : ''
        }
      })
      .filter(m => m.name.trim() || m.image.trim())
    const sponsors = (Array.isArray(g.sponsors) ? g.sponsors : [])
      .map((raw): { name: string, avatar: string, amount: string, date: string } => {
        const item = (raw ?? {}) as Record<string, unknown>
        const text = (v: unknown) => (typeof v === 'string' ? v.trim() : '')
        return {
          name: text(item.name),
          avatar: text(item.avatar),
          amount: text(item.amount),
          date: text(item.date)
        }
      })
      .filter(s => s.name)
    return {
      enable: g.enable !== false,
      title: pickI18n(g.title),
      description: pickI18n(g.description),
      methods,
      sponsors,
      show_sponsors_list: g.show_sponsors_list !== false
    }
  })

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
        // ====== 走公开端点 GET /api/settings/public ======
        // 旧的 GET /api/settings 是 admin-only：访客（含 SSR 匿名请求）必然 401，
        // 结果是 hero / footer / notice 等管理员配置在前台永远读不到，
        // 控制台还会刷一条 "Failed to load resource: 401"。
        // 后端已提供脱敏后的公开子集，这里改用该端点，彻底消除 401。
        try {
          const raw = await apiFetch<{ groups?: AllSettingsGroups }>('/settings/public', {
            method: 'GET'
          })
          if (raw && typeof raw === 'object' && raw.groups && typeof raw.groups === 'object') {
            state.value.groups = raw.groups as UseSiteState['groups']
          }
        } catch (e) {
          const status = (e as { status?: number })?.status ?? 0
          console.debug('[useSite] /settings/public fetch skipped:', status || 'network')
          /* OOBE / 后端不可达 → groups 保持空对象，computed 自动走 publicConfig 兜底 */
        }
      })(),
      (async () => {
        // ====== 主题 Customizer 预载 ======
        // 与站点 settings 并行加载，保证 computed 派生时 override.*.value 已就绪；
        // 失败则 theme 保持默认值，settings 继续兜底，用户永远不会看到空样式。
        try {
          await theme.ensureLoaded({ force: opts?.force })
        } catch { /* ignore */ }
      })()
    ])

    state.value.loaded = true
    // 先应用 settings 默认 token；theme 显式覆盖的颜色在 theme.ensureLoaded 中会再 apply 一遍
    // （比这里更晚），保证优先级顺序：theme > settings > CSS 定义。
    applyAppearanceTokens()
    theme.applyThemeColorTokens()
    return state.value
  }

  return {
    state,
    basic,
    seo,
    appearance,
    hero,
    footer,
    notice,
    reading,
    features,
    comments,
    navigation,
    donate,
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
