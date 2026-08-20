// 全局动态 titleTemplate 与品牌颜色 tokens 应用：
//  - 单一权威拼接："单页标题 · 站点名" / "站点名 · 副标题"
//  - 与 useSite composable 解耦：直接用 $fetch 打公开 /api/config，不走 useRuntimeConfig /
//    useAuthStore 等 composable，避免在 Vite diagnostics 热链路上触发 NUXT_E1001。
//  - 仅客户端生效（SSR 时由各页面 useSeoMeta/useHead 生成标题，避免双链路冲突）。

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
      default: break
    }
    h *= 60
  }
  return { h, s: s * 100, l: l * 100 }
}

function applyAppearance(primary: string, accent: string) {
  if (!import.meta.client) return
  const root = document.documentElement
  const a = hexToHsl(String(accent || '#0284C7'))
  if (a) {
    root.style.setProperty('--theme-accent-hue', String(Math.round(a.h)))
    root.style.setProperty('--theme-accent-sat', `${Math.round(a.s)}%`)
    root.style.setProperty('--theme-accent-light', `${Math.round(a.l)}%`)
  }
  const p = hexToHsl(String(primary || '#0EA5A9'))
  if (p) {
    root.style.setProperty('--primary', `${Math.round(p.h)} ${Math.round(p.s)}% ${Math.round(p.l)}%`)
    const ringL = Math.min(96, p.l * 1.12)
    root.style.setProperty('--ring', `${Math.round(p.h)} ${Math.round(p.s + 2)}% ${ringL}%`)
  }
}

interface BrandInfo {
  siteName: string
  siteSub: string
  primary: string
  accent: string
}

async function loadBrand(): Promise<BrandInfo> {
  const fallback: BrandInfo = { siteName: 'Rosetta', siteSub: '', primary: '#0EA5A9', accent: '#0284C7' }
  if (!import.meta.client) return fallback
  try {
    // 客户端相对路径 /api/config，经浏览器 devProxy → FastAPI :8000
    const cfg = await $fetch<Record<string, unknown>>('/api/config', {
      headers: { 'Accept-Language': document.documentElement.lang || navigator.language || 'zh-CN' }
    })
    if (cfg && typeof cfg === 'object') {
      if (typeof cfg.site_name === 'string' && cfg.site_name) fallback.siteName = cfg.site_name
      const sub = (cfg.site_subtitle ?? ((cfg as Record<string, unknown>).subtitle)) as unknown
      if (typeof sub === 'string' && sub) fallback.siteSub = sub
      if (typeof cfg.theme_primary === 'string') fallback.primary = cfg.theme_primary
      if (typeof cfg.theme_accent === 'string') fallback.accent = cfg.theme_accent
    }
  } catch { /* 后端不可用或 OOBE：使用默认值 */ }
  return fallback
}

let cached: Promise<BrandInfo> | null = null
const getBrand = (): Promise<BrandInfo> => {
  if (!cached) cached = loadBrand()
  return cached
}

export default defineNuxtPlugin(async () => {
  if (!import.meta.client) return

  // 先以默认值设置 titleTemplate（保证 SPA 跳转首屏也有统一拼接）
  const defaults: BrandInfo = { siteName: 'Rosetta', siteSub: '', primary: '#0EA5A9', accent: '#0284C7' }
  let siteName = defaults.siteName
  let siteSub = defaults.siteSub

  const buildTitle = (title?: string | undefined): string => {
    const t = String(title || '').trim()
    if (t) {
      if (t === siteName) return siteSub ? `${siteName} · ${siteSub}` : siteName
      return `${t} · ${siteName}`
    }
    return siteSub ? `${siteName} · ${siteSub}` : siteName
  }

  useHead({ titleTemplate: buildTitle })

  try {
    const brand = await getBrand()
    siteName = brand.siteName
    siteSub = brand.siteSub
    applyAppearance(brand.primary, brand.accent)
    // 品牌色/站点名加载完成后再刷新一次 titleTemplate（当前页面 title 不变，后缀却更新）
    useHead({ titleTemplate: buildTitle })
  } catch {
    applyAppearance(defaults.primary, defaults.accent)
  }
})
