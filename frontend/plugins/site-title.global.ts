// 全局动态 titleTemplate 与品牌颜色 tokens 应用：
//  - 单一权威拼接："单页标题 · 站点名" / "站点名 · 副标题"
//  - 与 useSite composable 解耦：直接用 $fetch 打公开 /api/config，不走 useRuntimeConfig /
//    useAuthStore 等 composable，避免在 Vite diagnostics 热链路上触发 NUXT_E1001。
//    （lib/utils 是无 Nuxt 上下文依赖的纯函数库，import 它不破坏该解耦）
//  - 仅客户端生效（SSR 时由各页面 useSeoMeta/useHead 生成标题，避免双链路冲突）。
import { hexToHsl } from '~~/lib/utils'

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
    // timeout + signal：保证 devProxy 异常（空 host/port、后端未就绪）时 10s 内 reject，
    // 避免 defineNuxtPlugin(async) 永远 pending 导致整个 SPA 白屏。
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 10000)
    const cfg = await $fetch<Record<string, unknown>>('/api/config', {
      headers: { 'Accept-Language': document.documentElement.lang || navigator.language || 'zh-CN' },
      signal: ctrl.signal,
      timeout: 10000
    })
    clearTimeout(timer)
    if (cfg && typeof cfg === 'object') {
      if (typeof cfg.site_name === 'string' && cfg.site_name) fallback.siteName = cfg.site_name
      const sub = (cfg.site_subtitle ?? ((cfg as Record<string, unknown>).subtitle)) as unknown
      if (typeof sub === 'string' && sub) fallback.siteSub = sub
      if (typeof cfg.theme_primary === 'string') fallback.primary = cfg.theme_primary
      if (typeof cfg.theme_accent === 'string') fallback.accent = cfg.theme_accent
    }
  } catch { /* 后端不可用 / OOBE / 超时：使用默认值 */ }
  return fallback
}

let cached: Promise<BrandInfo> | null = null
let cachedAt = 0
let brandCache: BrandInfo | null = null
const CACHE_MS = 60_000
const STORAGE_KEY = 'rosetta:brand:cache:v1'

function readPersisted(): BrandInfo | null {
  if (!import.meta.client) return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const v = JSON.parse(raw) as { exp: number, brand: BrandInfo }
    if (!v || !v.brand || typeof v !== 'object') return null
    if (v.exp > 0 && v.exp < Date.now()) return null
    return v.brand
  } catch { return null }
}
function writePersisted(b: BrandInfo) {
  if (!import.meta.client) return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ exp: Date.now() + CACHE_MS, brand: b }))
  } catch { /* storage quota */ }
}

const getBrand = (): Promise<BrandInfo> => {
  if (brandCache) return Promise.resolve(brandCache)
  if (cached && cachedAt > 0 && Date.now() - cachedAt < CACHE_MS) return cached
  const persisted = readPersisted()
  if (persisted && persisted.siteName) {
    // 优先用存储兜底，即便网络闪断首屏也不会再发 3 次重复请求
    brandCache = persisted
    cached = Promise.resolve(persisted)
    cachedAt = Date.now()
  }
  if (!cached) {
    cached = (async () => {
      const b = await loadBrand()
      brandCache = b
      cachedAt = Date.now()
      writePersisted(b)
      return b
    })()
  }
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
