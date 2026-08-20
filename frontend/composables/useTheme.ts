/**
 * Rosetta 全局主题管理（完全参考 https://w2xiaoyu.github.io/blog/front/view-transition-theme.html 实现）。
 *
 * 要点：
 *   1. 首选 View Transitions API（Chrome / Edge 111+ / Safari 18+）：
 *        const vt = document.startViewTransition(() => { isDark = !isDark })
 *      浏览器会自动「截图锁定」旧帧（::view-transition-old）与新帧（::view-transition-new），
 *      我们只需要给 ::view-transition-* 两个伪元素用 clip-path: circle() 做圆形扩散/收缩。
 *
 *   2. 方向：
 *        light -> dark：theme-grow   新主题在上（z-index 9999），circle(0 → 150%) 扩散
 *        dark -> light：theme-shrink 旧主题在上（z-index 9999），circle(150% → 0) 收缩
 *
 *   3. 常见坑全部按博客规避：
 *        - 纯 CSS @keyframes，不用 JS animate()
 *        - animation 带 forwards（防止 shrink 收尾瞬间回弹旧主题闪白/闪黑）
 *        - finished.then(...) 清 class，不用 ready
 *        - remove class → void root.offsetWidth → add class，强制 reflow 避免 class 变更被合并
 *
 *  4. Hydration 安全（重要）：
 *        - isDark / themeMode 必须走 Nuxt 共享的 useState，两端初始值统一 light/false，
 *          SSR 输出与客户端首渲染 DOM 字节级一致。
 *        - 不允许在 composable 顶层直接读 localStorage / matchMedia 并修改首渲染状态，
 *          否则 ThemeToggle 的 v-if 会导致 SVG 节点（Sun vs Moon）mismatch。
 *        - 真实用户偏好的应用时机：由 plugins/theme.client.ts 在 Hydrate 完成后调用
 *          initFromStorageAndApply() 同步更新 state + DOM classList（走 Vue patch，不触发 mismatch）。
 *
 * 存储：localStorage.theme 只存 'light' | 'dark'；旧值 'system' / 'rosetta-theme' 迁移。
 */

import type { ComponentPublicInstance } from 'vue'

const STORAGE_KEY = 'theme'
type ThemeMode = 'light' | 'dark'

export interface RippleOrigin {
  clientX: number
  clientY: number
}

/** 简化的 fallback ripple 兜底（非 VT 环境的纯色 mask，动画参数） */
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
    if (runningTimer !== null) {
      window.clearTimeout(runningTimer)
      runningTimer = null
    }
    if (fadeTimer !== null) {
      window.clearTimeout(fadeTimer)
      fadeTimer = null
    }
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
    progress.value = opts.startProgress
    fade.value = 1

    state.startProgress = opts.startProgress
    state.endProgress = opts.endProgress
    state.maxRadius = opts.maxRadius
    state.cx = opts.cx
    state.cy = opts.cy
    state.background = opts.background
    state.target = opts.target
    state.visible = true

    await nextTick()
    await nextFrame(2)

    const isExpand = opts.endProgress > opts.startProgress
    if (!isExpand) opts.flipTheme()

    progress.value = opts.endProgress

    const THEME_RIPPLE_DURATION = 520
    if (isExpand) {
      runningTimer = window.setTimeout(() => opts.flipTheme(), Math.round(THEME_RIPPLE_DURATION * 0.62))
    }
    runningTimer = window.setTimeout(() => {
      fade.value = 0
      fadeTimer = window.setTimeout(() => {
        state.visible = false
        fade.value = 1
      }, 200)
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

function probeAbsoluteBackground(): { light: string, dark: string } {
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
    const r = Number(m[1])
    const g = Number(m[2])
    const b = Number(m[3])
    return '#' + toHex(r) + toHex(g) + toHex(b)
  }
  root.classList.remove('dark')
  const lightHsl = getComputedStyle(root).getPropertyValue('--background').trim() || '0 0% 100%'
  const light = hslToHex(lightHsl, '#ffffff')
  root.classList.add('dark')
  const darkHsl = getComputedStyle(root).getPropertyValue('--background').trim() || '224 71% 4%'
  const dark = hslToHex(darkHsl, '#0b1020')
  if (wasDark) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
  return { light, dark }
}

export function resolveRippleOrigin(
  origin?: RippleOrigin | MouseEvent | null,
  fallbackEl?: Element | ComponentPublicInstance | null
): { cx: number, cy: number } {
  if (!import.meta.client || typeof window === 'undefined') return { cx: 720, cy: 450 }
  if (origin && typeof origin === 'object' && Number.isFinite((origin as { clientX: unknown }).clientX)) {
    return {
      cx: Math.max(0, Math.min(window.innerWidth, (origin as RippleOrigin).clientX)),
      cy: Math.max(0, Math.min(window.innerHeight, (origin as RippleOrigin).clientY))
    }
  }
  let el: Element | null = null
  if (fallbackEl) {
    if (fallbackEl instanceof Element) el = fallbackEl
    else if ((fallbackEl as { $el: unknown }).$el instanceof Element) el = (fallbackEl as { $el: Element }).$el
  }
  if (el) {
    const r = el.getBoundingClientRect()
    return { cx: r.left + r.width / 2, cy: r.top + r.height / 2 }
  }
  return { cx: window.innerWidth / 2, cy: window.innerHeight / 2 }
}

export function useTheme() {
  // SSR & 客户端首渲染 统一用 false / 'light'，保证字节级一致
  const isDark = useState<boolean>('theme-dark', () => false)
  const themeMode = useState<ThemeMode>('theme-mode', () => 'light')
  const ripple = useThemeRipple()

  const _getSystemDark = () => {
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

  /**
   * 同步应用主题到：① 共享 useState（驱动 Vue 组件重渲染/切换图标）
   *                  ② <html>.classList（驱动 Tailwind dark: 选择器与 CSS 变量）
   *                  ③ theme-color meta
   * Hydrate 完成后调用是安全的：Vue 会走 patch，不会触发 mismatch。
   */
  const applyTheme = (dark: boolean) => {
    isDark.value = dark
    themeMode.value = dark ? 'dark' : 'light'
    if (import.meta.client && typeof document !== 'undefined') {
      const root = document.documentElement
      if (dark) {
        root.classList.add('dark')
      } else {
        root.classList.remove('dark')
      }
      syncMetaThemeColor(dark)
    }
  }

  const persist = () => {
    if (import.meta.client && typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, themeMode.value)
      try {
        localStorage.removeItem('rosetta-theme')
      } catch {
        /* noop */
      }
    }
  }

  const setLight = () => {
    ripple.stop()
    applyTheme(false)
    persist()
  }
  const setDark = () => {
    ripple.stop()
    applyTheme(true)
    persist()
  }

  /**
   * 在 Hydrate 完成后调用：读取用户偏好 → 同步写入共享 useState & DOM classList。
   * 由 plugins/theme.client.ts 调用（在 window.load / setTimeout 0 之后）。
   */
  const initFromStorageAndApply = () => {
    if (!import.meta.client) return
    let prefersDark = false
    try {
      prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    } catch {
      prefersDark = prefersDark || false
    }
    let stored: string | null
    try {
      const legacy = localStorage.getItem('rosetta-theme')
      stored = localStorage.getItem(STORAGE_KEY)
      if (!stored && legacy) stored = legacy
    } catch {
      stored = null
    }
    if (stored === undefined) stored = null

    const nextDark = stored === 'dark' || (stored !== 'light' && prefersDark)
    applyTheme(nextDark)
    persist()
  }

  /**
   * 完全按参考博客实现主题切换动画：
   *   enableTransitions = startViewTransition 存在 且 prefers-reduced-motion 未开启
   *   willBeDark 提前取（切换后 isDark 会被改写，判断会反）
   *   --reveal-cx / --reveal-cy：点击坐标写 root style
   *   remove grow/shrink → void offsetWidth → add 目标方向 class
   *   vt.finished.then(cleanup)
   */
  const toggle = async (origin?: RippleOrigin | MouseEvent | null, fallbackEl?: Element | ComponentPublicInstance | null) => {
    if (!import.meta.client) {
      if (isDark.value) {
        setLight()
      } else {
        setDark()
      }
      return
    }
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const enableTransitions = typeof (document as Document & { startViewTransition?: unknown }).startViewTransition === 'function' && !reducedMotion

    // 非 VT 环境：走最简单的「纯色 mask 遮罩」兜底
    if (!enableTransitions) {
      const wasDark = isDark.value
      const nextDark = !wasDark
      const nextMode: ThemeMode = nextDark ? 'dark' : 'light'
      const { cx, cy } = resolveRippleOrigin(origin, fallbackEl)
      const vw = window.innerWidth || 1440
      const vh = window.innerHeight || 900
      const maxRadius = Math.ceil(Math.max(Math.hypot(cx, cy), Math.hypot(vw - cx, cy), Math.hypot(cx, vh - cy), Math.hypot(vw - cx, vh - cy))) + 4
      const bg = probeAbsoluteBackground()
      await ripple.play({
        startProgress: wasDark ? 1 : 0,
        endProgress: wasDark ? 0 : 1,
        maxRadius,
        cx,
        cy,
        background: nextDark ? bg.dark : bg.light,
        target: nextMode,
        flipTheme: () => {
          applyTheme(nextDark)
          persist()
        }
      })
      return
    }

    // 1:1 复制博客写法
    const willBeDark = !isDark.value
    const root = document.documentElement as HTMLElement
    const { cx, cy } = resolveRippleOrigin(origin, fallbackEl)

    root.style.setProperty('--reveal-cx', cx + 'px')
    root.style.setProperty('--reveal-cy', cy + 'px')

    root.classList.remove('theme-grow', 'theme-shrink')
    void root.offsetWidth // 强制 reflow
    root.classList.add(willBeDark ? 'theme-grow' : 'theme-shrink')

    const transition = (document as Document & { startViewTransition?: (fn: () => void) => void }).startViewTransition!(() => {
      applyTheme(willBeDark)
      persist()
      return nextTick()
    })

    transition.finished.then(() => {
      root.classList.remove('theme-grow', 'theme-shrink')
      root.style.removeProperty('--reveal-cx')
      root.style.removeProperty('--reveal-cy')
    }).catch(() => { /* noop */ })
  }

  return { isDark, themeMode, toggle, setLight, setDark, initFromStorageAndApply }
}
