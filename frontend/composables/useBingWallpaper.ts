/**
 * Bing 每日壁纸组合式函数
 *
 * 注意：
 *  1. useRuntimeConfig / useI18n 必须在 composable 顶层（setup/顶层上下文）直接调用，
 *     不能嵌套在 async 内部函数里，否则 Nuxt 会抛 NUXT_E1001（"composable called
 *     outside a plugin / Nuxt hook / Nuxt middleware / Vue setup"），
 *     严重时会打断 hydration，导致整页白屏。
 *  2. localStorage / fetch 直连 Bing 仅客户端可用，使用 import.meta.client 守卫。
 */
export interface BingImage {
  url: string
  urlbase: string
  copyright: string
  copyrightlink: string
  title: string
  startdate: string
  enddate: string
  fullUrl: string
  uhdUrl: string
  dayOffset: number
}

/** Bing HPImageArchive 接口返回的原始图片字段 */
interface BingRawImage {
  url?: string
  urlbase?: string
  copyright?: string
  copyrightlink?: string
  title?: string
  startdate?: string
  enddate?: string
}

const WALLPAPER_MONTHS_LABEL: Record<string, string[]> = {
  zh: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  zh_Hant: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  ja: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
}

const WALLPAPER_MONTHS_COMPACT_EN: string[] = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

export const useBingWallpaper = () => {
  // ===== Nuxt / Vue 上下文必须在 composable 顶层调用，避免 NUXT_E1001 =====
  const runtimeConfig = useRuntimeConfig()
  const { locale: i18nLocale } = useI18n()
  const apiBase = computed(() => (runtimeConfig.public.apiBase as string) || '')

  const images = ref<BingImage[]>([])
  const loading = ref(false)
  const error = ref<unknown>(null)
  const currentIdx = ref(0)

  const currentImage = computed<BingImage | null>(() => {
    if (images.value.length === 0) return null
    return images.value[Math.min(currentIdx.value, images.value.length - 1)] || null
  })

  const formatDayLabel = (enddate: string, offset: number) => {
    if (!enddate || enddate.length < 8) {
      return offset === 0 ? '今天' : `-${offset}天`
    }
    const m = enddate.substring(4, 6)
    const d = enddate.substring(6, 8)
    const locale = (i18nLocale.value as string) || 'zh'
    const months = (WALLPAPER_MONTHS_LABEL[locale] || WALLPAPER_MONTHS_LABEL.en || []) as string[]
    const monthStr = months[parseInt(m, 10) - 1] || m
    const dayNum = String(parseInt(d, 10))
    switch (locale) {
      case 'zh':
      case 'zh_Hant':
      case 'ja':
        return `${monthStr}${dayNum}日`
      case 'en':
      default:
        return `${monthStr} ${dayNum}`
    }
  }

  const formatDateCompact = (enddate: string, offset: number) => {
    if (offset === 0) return { main: '今', sub: 'Today' } as const
    if (!enddate || enddate.length < 8) {
      return { main: String(offset), sub: 'days ago' } as const
    }
    const m = enddate.substring(4, 6)
    const d = enddate.substring(6, 8)
    // ⚠️ 必须复用顶层 i18nLocale（已经在 composable 开头通过 useI18n() 拿到），
    //    禁止再次调用 useI18n()，避免离开 setup 上下文时触发 NUXT_E1001。
    const locale = (i18nLocale.value as string) || 'zh'
    const monthInt = parseInt(m, 10)
    let sub: string
    switch (locale) {
      case 'zh':
      case 'zh_Hant':
      case 'ja':
        sub = `${monthInt}月`
        break
      case 'en':
      default:
        sub = WALLPAPER_MONTHS_COMPACT_EN[monthInt - 1] || String(monthInt)
    }
    return { main: String(parseInt(d, 10)), sub } as const
  }

  const recentDays = computed(() => {
    return images.value.slice(0, 8).map((img, i) => {
      let thumbnail: string
      if (img.urlbase) {
        // Bing 官方缩略图 CDN
        thumbnail = `https://www.bing.com${img.urlbase}_150x150.jpg`
      } else if (img.fullUrl && /unsplash\.com|picsum\.photos|images\.unsplash/i.test(img.fullUrl)) {
        // Unsplash/Picsum 等支持参数的图片源：替换宽度参数或附加为缩略图
        let u = img.fullUrl
        if (u.includes('w=')) u = u.replace(/w=\d+/, 'w=320')
        else u += (u.includes('?') ? '&' : '?') + 'w=320&q=60'
        thumbnail = u
      } else {
        // 其他源：直接复用原图（浏览器会自动缩放到缩略图尺寸）
        thumbnail = img.fullUrl
      }
      return {
        index: i,
        label: formatDayLabel(img.enddate, i),
        dateCompact: formatDateCompact(img.enddate, i),
        title: img.title || '',
        thumbnail
      }
    })
  })

  const selectDay = (i: number) => {
    if (i >= 0 && i < images.value.length) {
      currentIdx.value = i
      if (import.meta.client) {
        try {
          localStorage.setItem('bing_wallpaper_idx', String(i))
        } catch { /* ignore */ }
      }
    }
  }

  const parseImages = (rawImages: BingRawImage[]): BingImage[] => {
    return (rawImages || []).map((img: BingRawImage, i: number) => {
      const url = img.url || ''
      const uhdUrl = (img.urlbase || '') + '_UHD.jpg'
      const fullUrl = url.startsWith('http') ? url : `https://www.bing.com${url}`
      return {
        url,
        urlbase: img.urlbase || '',
        copyright: img.copyright || '',
        copyrightlink: img.copyrightlink || '',
        title: img.title || '',
        startdate: img.startdate || '',
        enddate: img.enddate || '',
        fullUrl,
        uhdUrl: uhdUrl.startsWith('http') ? uhdUrl : `https://www.bing.com${uhdUrl}`,
        dayOffset: i
      }
    })
  }

  const fetchWallpapers = async () => {
    loading.value = true
    error.value = null
    try {
      // 尝试读取上次选择（客户端守卫，避免 SSR/localStorage 不可用）
      if (import.meta.client) {
        try {
          const saved = localStorage.getItem('bing_wallpaper_idx')
          if (saved != null) currentIdx.value = Math.max(0, Math.min(7, parseInt(saved, 10) || 0))
        } catch { /* ignore */ }
      }

      // 优先走后端代理（无 CORS 问题，且带缓存）；失败再回退直连 Bing
      const loadFromBackend = async (): Promise<BingImage[]> => {
        interface ProxyImage {
          url?: string
          urlbase?: string
          full_url?: string
          uhd_url?: string
          title?: string
          copyright?: string
          copyright_link?: string
          startdate?: string
          enddate?: string
        }
        const data = await $fetch<{ images?: ProxyImage[] }>('/bing/wallpapers', {
          baseURL: apiBase.value,
          query: { n: 8, market: 'zh-CN' }
        })
        return (data.images || []).map((img, i) => ({
          url: img.url || '',
          urlbase: img.urlbase || '',
          copyright: img.copyright || '',
          copyrightlink: img.copyright_link || '',
          title: img.title || '',
          startdate: img.startdate || '',
          enddate: img.enddate || '',
          fullUrl: img.full_url || '',
          uhdUrl: img.uhd_url || '',
          dayOffset: i
        }))
      }

      const loadFromBingDirect = async (): Promise<BingImage[]> => {
        if (!import.meta.client) return []
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 6000)
        try {
          const resp = await fetch(
            'https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=zh-CN',
            { signal: controller.signal }
          )
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
          const data = await resp.json()
          const list = parseImages(data.images)
          if (list.length === 0) throw new Error('empty')
          return list
        } finally {
          clearTimeout(timeoutId)
        }
      }

      let list: BingImage[] = []
      try {
        list = await loadFromBackend()
      } catch {
        // 后端代理不可用（如 OOBE 阶段后端未启动）：回退直连
        try {
          list = await loadFromBingDirect()
        } catch (e) {
          console.warn('[bing-wallpaper] API unavailable, hero will fall back to gradient.', e)
        }
      }
      images.value = list
    } catch (e) {
      error.value = e
      images.value = []
    } finally {
      loading.value = false
    }
    return images.value
  }

  return {
    images,
    loading,
    error,
    currentIdx,
    currentImage,
    recentDays,
    selectDay,
    fetchWallpapers
  }
}
