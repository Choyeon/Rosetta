/**
 * Bing 每日壁纸组合式函数
 * API: https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=zh-CN
 * idx: 起始偏移 (0=今天, 1=昨天, ...7=7天前)
 * n: 返回数量 (最多 8，即最近 8 天)
 * 返回字段：{ images: [{ url, copyright, title, enddate, startdate, ... }] }
 * 图片 URL 相对域名为 https://www.bing.com
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

export const useBingWallpaper = () => {
  const images = ref<BingImage[]>([])
  const loading = ref(false)
  const error = ref<unknown>(null)
  const currentIdx = ref(0)

  const currentImage = computed<BingImage | null>(() => {
    if (images.value.length === 0) return null
    return images.value[Math.min(currentIdx.value, images.value.length - 1)] || null
  })

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
      try {
        localStorage.setItem('bing_wallpaper_idx', String(i))
      } catch { /* ignore */ }
    }
  }

  const formatDayLabel = (enddate: string, offset: number) => {
    if (!enddate || enddate.length < 8) {
      return offset === 0 ? '今天' : `-${offset}天`
    }
    const y = enddate.substring(0, 4)
    const m = enddate.substring(4, 6)
    const d = enddate.substring(6, 8)
    const locale = (useI18n?.()?.locale?.value as string) || 'zh'
    try {
      const date = new Date(`${y}-${m}-${d}`)
      return date.toLocaleDateString(locale, { month: 'short', day: 'numeric' })
    } catch {
      return `${m}/${d}`
    }
  }

  const formatDateCompact = (enddate: string, offset: number) => {
    if (offset === 0) return { main: '今', sub: 'Today' } as const
    if (!enddate || enddate.length < 8) {
      return { main: String(offset), sub: 'days ago' } as const
    }
    const m = enddate.substring(4, 6)
    const d = enddate.substring(6, 8)
    return { main: d, sub: `${parseInt(m, 10)}月` } as const
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

  const loadMockFallback = (): BingImage[] => {
    // 无网络时的占位：返回几张高质量 Unsplash 照片 + 假版权
    const placeholders = [
      { url: 'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1920&q=80', title: '山川湖泊', copyright: '© Unsplash / Eberhard Grossgasteiger' },
      { url: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1920&q=80', title: '松林雾霭', copyright: '© Unsplash / Noah Silliman' },
      { url: 'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1920&q=80', title: '秋色山谷', copyright: '© Unsplash / Eberhard Grossgasteiger' },
      { url: 'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1920&q=80', title: '海岸灯塔', copyright: '© Unsplash / Robert Lukeman' },
      { url: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1920&q=80', title: '雪岭之巅', copyright: '© Unsplash / Federico Beccari' },
      { url: 'https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=1920&q=80', title: '森林瀑布', copyright: '© Unsplash / Eberhard Grossgasteiger' },
      { url: 'https://images.unsplash.com/photo-1475924156734-496f6cac6ec1?w=1920&q=80', title: '极光之夜', copyright: '© Unsplash / Luke Stackpoole' },
      { url: 'https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=1920&q=80', title: '林间小径', copyright: '© Unsplash / Casey Horner' }
    ]
    const now = new Date()
    return placeholders.map((p, i) => {
      const d = new Date(now)
      d.setDate(now.getDate() - i)
      const enddate = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
      return {
        url: p.url,
        urlbase: '',
        copyright: p.copyright,
        copyrightlink: 'https://unsplash.com/',
        title: p.title,
        startdate: enddate,
        enddate,
        fullUrl: p.url,
        uhdUrl: p.url,
        dayOffset: i
      }
    })
  }

  const fetchWallpapers = async () => {
    loading.value = true
    error.value = null
    try {
      // 尝试读取上次选择
      try {
        const saved = localStorage.getItem('bing_wallpaper_idx')
        if (saved != null) currentIdx.value = Math.max(0, Math.min(7, parseInt(saved, 10) || 0))
      } catch { /* ignore */ }

      // 优先走后端代理（无 CORS 问题，且带缓存）；失败再回退直连 Bing，最后本地兜底
      const loadFromBackend = async (): Promise<BingImage[]> => {
        const apiBase = useRuntimeConfig().public.apiBase as string
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
          baseURL: apiBase,
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
          console.warn('[bing-wallpaper] API unavailable, using local fallback images.', e)
        }
      }
      if (list.length === 0) list = loadMockFallback()
      images.value = list
    } catch (e) {
      error.value = e
      images.value = loadMockFallback()
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
