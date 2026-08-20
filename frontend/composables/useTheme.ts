/**
 * Rosetta 全局主题管理（与 ThemeToggle.vue / theme.client.ts / 全局
 * app.vue 中的 <ThemeRippleOverlay /> 保持一致）。
 *
 * 存储规范（与 project_memory 对齐）：
 *   localStorage.theme 只能存 'light' | 'dark'
 *   旧值 'system' / 'rosetta-theme' 会在 init 时迁移为当前系统主题对应的值。
 *
 * 切换动画（彻底解决亮/暗切换黑屏白屏闪屏）：
 *   采用「圆形扩散 / 收缩」mask：
 *     - light -> dark：遮罩为目标暗色背景，circle(0 -> R)，圆形从点击点扩出来，
 *       当 circle 覆盖整个视窗时，视觉上已经是暗色，再悄悄切 .dark 类，随后遮罩淡出。
 *     - dark -> light：先切底层 .dark 类（此时全屏仍被遮罩=旧暗色挡住），
 *       然后 circle(R -> 0) 向点击点收缩，露出底下的亮色。
 *   全程由 CSS @property --theme-ripple-progress + transition 驱动，
 *   首帧用「双 rAF」保证不会跳帧。
 */

import type { ComponentPublicInstance } from 'vue'

const STORAGE_KEY = 'theme'
type ThemeMode = 'light' | 'dark'

export const THEME_RIPPLE_DURATION = 960
export const THEME_RIPPLE_EASING = 'cubic-bezier(0.22, 1, 0.36, 1)'

export interface RippleOrigin {
  clientX: number
  clientY: number
}

export interface ThemeRippleState {
  visible: boolean
  startProgress: number
  endProgress: number
  maxRadius: number
  cx: number
  cy: number
  background: string
  target: ThemeMode
}

const DEFAULT_RIPPLE: Readonly<ThemeRippleState> = Object.freeze<ThemeRippleState>({
  visible: false,
  startProgress: 0,
  endProgress: 1,
  maxRadius: 2000,
  cx: 0,
  cy: 0,
  background: '#ffffff',
  target: 'light'
})

let __themeRippleSingleton: ReturnType<typeof createRippleState> | null = null

function createRippleState() {
  const state = reactive<ThemeRippleState>({ ...DEFAULT_RIPPLE })
  const progress = ref<number>(0)
  const fade = ref<number>(1)
  let runningTimer: number | null = null
  let fadeTimer: number | null = null

  const nextFrame = (frames = 1): Promise<void> =>
    new Promise<void>((resolve) => {
      let n = frames
      const tick = () => {
        n--
        if (n <= 0) resolve()
        else requestAnimationFrame(tick)
      }
      requestAnimationFrame(tick)
    })

  const clearTimers = () => {
    if (runningTimer !== null) { window.clearTimeout(runningTimer); runningTimer = null }
    if (fadeTimer !== null) { window.clearTimeout(fadeTimer); fadeTimer = null }
  }

  const play = async (opts: {
    startProgress: number
    endProgress: number
    maxRadius: number
    cx: number
    cy: number
    background: string
    target: ThemeMode
    flipTheme: () => void
  }) => {
    if (!import.meta.client) return

    clearTimers()
    state.visible = false
    progress.value = 0
    fade.value = 1

    state.startProgress = opts.startProgress
    state.endProgress = opts.endProgress
    state.maxRadius = opts.maxRadius
    state.cx = opts.cx
    state.cy = opts.cy
    state.background = opts.background
    state.target = opts.target
    progress.value = opts.startProgress
    fade.value = 1
    state.visible = true

    await nextTick()
    await nextFrame(2)

    const isExpand = opts.endProgress > opts.startProgress
    if (!isExpand) opts.flipTheme()

    progress.value = opts.endProgress

    if (isExpand) {
      runningTimer = window.setTimeout(() => opts.flipTheme(), Math.round(THEME_RIPPLE_DURATION * 0.62))
    }

    runningTimer = window.setTimeout(() => {
      fade.value = 0
      fadeTimer = window.setTimeout(() => {
        state.visible = false
        fade.value = 1
      }, 220)
    }, THEME_RIPPLE_DURATION + 40)
  }

  const stop = () => {
    clearTimers()
    state.visible = false
    progress.value = 0
    fade.value = 1
  }

  return { state, progress, fade, play, stop }
}

export function useThemeRipple() {
  if (!__themeRippleSingleton) __themeRippleSingleton = createRippleState()
  return __themeRippleSingleton!
}

function probeAbsoluteBackground(): { light: string; dark: string } {
  if (!import.meta.client || typeof document === 'undefined') return { light: '#ffffff', dark: '#0b1020' }
  const root = document.documentElement
  const wasDark = root.classList.contains('dark')
  const hslToHex = (hsl: string, fallback: string): string => {
    const probe = document.createElement('div')
    probe.style.cssText = 'position:absolute;left:-9999px;top:-9999px;width:1px;height:1px;background:hsl(' + hsl + ')'
    document.body.appendChild(probe)
    const raw = window.getComputedStyle(probe).backgroundColor
    probe.remove()
    const m = raw.match(/rgba?\(([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/)
    if (!m) return fallback
    const toHex = (v: number) => Math.min(255, Math.max(0, Math.round(v))).toString(16).padStart(2, '0')
    const r = Number(m[1]); const g = Number(m[2]); const b = Number(m[3])
    return '#' + toHex(r) + toHex(g) + toHex(b)
  }
  root.classList.remove('dark')
  const lightHsl = getComputedStyle(root).getPropertyValue('--background').trim() || '0 0% 100%'
  const light = hslToHex(lightHsl, '#ffffff')
  root.classList.add('dark')
  const darkHsl = getComputedStyle(root).getPropertyValue('--background').trim() || '224 71% 4%'
  const dark = hslToHex(darkHsl, '#0b1020')
  if (wasDark) root.classList.add('dark'); else root.classList.remove('dark')
  return { light, dark }
}

export function computeRippleRadius(cx: number, cy: number) {
  if (!import.meta.client || typeof window === 'undefined') return 2000
  const vw = window.innerWidth || 1440
  const vh = window.innerHeight || 900
  const corners = [{ x: 0, y: 0 }, { x: vw, y: 0 }, { x: 0, y: vh }, { x: vw, y: vh }]
  let max = 0
  for (const c of corners) {
    const d = Math.hypot(c.x - cx, c.y - cy)
    if (d > max) max = d
  }
  return Math.ceil(max) + 4
}

export function resolveRippleOrigin(
  origin?: RippleOrigin | MouseEvent | null,
  fallbackEl?: Element | ComponentPublicInstance | null
): { cx: number; cy: number } {
  if (!import.meta.client || typeof window === 'undefined') return { cx: 720, cy: 450 }
  if (origin && typeof origin === 'object' && Number.isFinite((origin as any).clientX)) {
    return {
      cx: Math.max(0, Math.min(window.innerWidth, (origin as RippleOrigin).clientX)),
      cy: Math.max(0, Math.min(window.innerHeight, (origin as RippleOrigin).clientY))
    }
  }
  let el: Element | null = null
  if (fallbackEl) {
    if (fallbackEl instanceof Element) el = fallbackEl
    else if ((fallbackEl as any).$el instanceof Element) el = (fallbackEl as any).$el as Element
  }
  if (el) {
    const r = el.getBoundingClientRect()
    return { cx: r.left + r.width / 2, cy: r.top + r.height / 2 }
  }
  return { cx: window.innerWidth / 2, cy: window.innerHeight / 2 }
}

export function useTheme() {
  const isDark = ref(false)
  const themeMode = ref<ThemeMode>('light')
  const ripple = useThemeRipple()

  const getSystemDark = () => {
    if (import.meta.client && typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return false
  }

  const syncMetaThemeColor = (dark: boolean) => {
    if (!import.meta.client) return
    const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
    if (!meta) return
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--background').trim()
    meta.content = bg ? 'hsl(' + bg + ')' : dark ? '#0b1020' : '#ffffff'
  }

  const applyTheme = (dark: boolean) => {
    if (import.meta.client && typeof document !== 'undefined') {
      const root = document.documentElement
      if (dark) root.classList.add('dark'); else root.classList.remove('dark')
      syncMetaThemeColor(dark)
    }
    isDark.value = dark
  }

  const persist = () => {
    if (import.meta.client && typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, themeMode.value)
      try { localStorage.removeItem('rosetta-theme') } catch { /* noop */ }
    }
  }

  const setLight = () => {
    themeMode.value = 'light'
    ripple.stop()
    applyTheme(false)
    persist()
  }
  const setDark = () => {
    themeMode.value = 'dark'
    ripple.stop()
    applyTheme(true)
    persist()
  }

  const toggle = async (origin?: RippleOrigin | MouseEvent | null, fallbackEl?: Element | ComponentPublicInstance | null) => {
    if (!import.meta.client) { if (isDark.value) setLight(); else setDark(); return }
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reducedMotion) { if (isDark.value) setLight(); else setDark(); return }

    const wasDark = isDark.value
    const nextDark = !wasDark
    const nextMode: ThemeMode = nextDark ? 'dark' : 'light'
    const { cx, cy } = resolveRippleOrigin(origin, fallbackEl)
    const maxRadius = computeRippleRadius(cx, cy)
    const bg = probeAbsoluteBackground()

    themeMode.value = nextMode
    persist()

    await ripple.play({
      startProgress: wasDark ? 1 : 0,
      endProgress: wasDark ? 0 : 1,
      maxRadius,
      cx,
      cy,
      background: nextDark ? bg.dark : bg.light,
      target: nextMode,
      flipTheme: () => applyTheme(nextDark)
    })
  }

  const init = () => {
    if (!import.meta.client) return
    try {
      const legacy = localStorage.getItem('rosetta-theme')
      let stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | string | null
      if (!stored && legacy) stored = legacy
      if (stored === 'dark') themeMode.value = 'dark'
      else if (stored === 'light') themeMode.value = 'light'
      else themeMode.value = getSystemDark() ? 'dark' : 'light'
    } catch {
      themeMode.value = getSystemDark() ? 'dark' : 'light'
    }
    applyTheme(themeMode.value === 'dark')
    persist()
  }

  init()

  return { isDark, toggle, setLight, setDark }
}
