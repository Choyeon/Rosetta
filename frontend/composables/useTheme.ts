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
  /** 底色兜底：截图未加载时显示的纯色 */
  background: string
  target: ThemeMode
  /** 旧主题页面截图（整层铺满，动画期间锁定屏幕，显示真实页面而非纯色） */
  beforeImage: string
  /** 新主题页面截图（只在 circle 揭示区显示，显示切换后的真实内容） */
  afterImage: string
}

const DEFAULT_RIPPLE: Readonly<ThemeRippleState> = Object.freeze<ThemeRippleState>({
  visible: false,
  startProgress: 0,
  endProgress: 1,
  maxRadius: 2000,
  cx: 0,
  cy: 0,
  background: '#ffffff',
  target: 'light',
  beforeImage: '',
  afterImage: ''
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
    beforeImage?: string
    afterImage?: string
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
    state.beforeImage = opts.beforeImage ?? ''
    state.afterImage = opts.afterImage ?? ''
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


/**
 * 主题切换的「截图锁定」：
 *   动画期间把「旧主题」和「目标主题」都预先渲染成离屏 <canvas>/dataURL，
 *   用两层叠加 + clip-path circle 揭示新主题。这样用户看到的是旧/新页面真实内容，
 *   而不是纯色遮罩纯黑/纯白。
 *
 * 实现策略（按优先级尝试，全部失败才回退到纯色 mask）：
 *   1) Document Picture-in-Picture / getDisplayMedia 需要权限/弹窗 → 跳过。
 *   2) View Transition API（Chrome 111+）：最干净，浏览器自己做前后帧捕捉 + ::view-transition-old/new 两层。
 *   3) 手动方案：
 *        a. 离屏 iframe 克隆 documentElement.outerHTML + 同步 CSS，强制 palette/dark 类；
 *        b. 再把 iframe 内容画进 canvas（同源所以允许）；
 *   4) 都失败 → 回退旧版纯色遮罩。
 */

let __iframeSnapshotHelper: HTMLIFrameElement | null = null
function getSnapshotHelper(): HTMLIFrameElement | null {
  if (typeof document === 'undefined') return null
  if (__iframeSnapshotHelper && __iframeSnapshotHelper.parentNode) return __iframeSnapshotHelper
  const iframe = document.createElement('iframe')
  iframe.setAttribute(
    'style',
    'position:fixed;left:-99999px;top:-99999px;width:100vw;height:100vh;z-index:-1;' +
    'border:0;padding:0;margin:0;pointer-events:none;visibility:hidden;background:transparent;'
  )
  iframe.sandbox.add('allow-same-origin')
  document.documentElement.appendChild(iframe)
  __iframeSnapshotHelper = iframe
  return iframe
}

interface SnapshotOptions {
  /** 要截图的主题：light / dark */
  targetTheme: 'light' | 'dark'
  palette?: string
}

/**
 * 把当前 document 克隆到离屏 iframe 并强制目标主题类，然后绘制到 canvas。
 * 返回 dataURL(image/png)，可以直接用作 overlay background-image。
 */
async function snapshotThemePage(opts: SnapshotOptions): Promise<{ dataUrl: string; width: number; height: number } | null> {
  if (!import.meta.client || typeof document === 'undefined') return null
  const w = Math.max(1, window.innerWidth)
  const h = Math.max(1, window.innerHeight)
  const dpr = Math.min(2, window.devicePixelRatio || 1)

  // 优先尝试 View Transition：这里不画图，只在调用方用 API 包裹整个 DOM 切换即可；
  // 所以 snapshot 失败时，调用方会走 VT。

  const iframe = getSnapshotHelper()
  if (!iframe) return null
  const idoc = iframe.contentDocument
  if (!idoc) return null
  const iwin = iframe.contentWindow
  if (!iwin) return null

  // 同步原始 HTML（head + body + html attrs），强制去掉交互 script
  const html = document.documentElement
  const clone = html.cloneNode(true) as HTMLElement
  // 强制主题类
  clone.classList.remove('dark')
  if (opts.targetTheme === 'dark') clone.classList.add('dark')
  // 强制调色板类
  if (opts.palette) {
    for (const cls of Array.from(clone.classList)) {
      if (cls.startsWith('palette-')) clone.classList.remove(cls)
    }
    clone.classList.add(`palette-${opts.palette}`)
  }
  clone.setAttribute('data-theme-snapshot', '1')

  const markup = '<!doctype html>' + clone.outerHTML
  idoc.open()
  try { idoc.write(markup) } catch { return null }
  idoc.close()

  // 等待 iframe 首帧布局（CSS 字体/外链需要一段时间；给 180ms 上限）
  await new Promise<void>(resolve => {
    let settled = false
    const doResolve = () => { if (!settled) { settled = true; resolve() } }
    idoc.addEventListener('DOMContentLoaded', doResolve, { once: true })
    iwin.addEventListener('load', doResolve, { once: true })
    setTimeout(doResolve, 260)
    // 某些情况下事件不触发，主动再兜底：下一帧后判 readyState
    requestAnimationFrame(() => {
      setTimeout(() => {
        if (idoc.readyState === 'complete' || idoc.readyState === 'interactive') doResolve()
        else setTimeout(doResolve, 100)
      }, 50)
    })
  })

  // 用 foreignObject 把 iframe root SVG-in-canvas 截图（同源内容无 taint）
  try {
    const rootRect = (idoc.documentElement || idoc.body).getBoundingClientRect()
    const svgNS = 'http://www.w3.org/2000/svg'
    const svg = idoc.createElementNS(svgNS, 'svg') as unknown as SVGSVGElement
    const width = Math.ceil(w)
    const height = Math.ceil(h)
    svg.setAttribute('xmlns', svgNS)
    svg.setAttribute('width', String(width * dpr))
    svg.setAttribute('height', String(height * dpr))
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`)
    const foreignObject = idoc.createElementNS(svgNS, 'foreignObject') as unknown as SVGForeignObjectElement
    foreignObject.setAttribute('width', String(width))
    foreignObject.setAttribute('height', String(height))
    foreignObject.setAttribute('x', '0')
    foreignObject.setAttribute('y', '0')
    // xhtml body 需要命名空间
    const xhtml =
      '<html xmlns="http://www.w3.org/1999/xhtml">' +
      idoc.documentElement.innerHTML +
      '</html>'
    // 强制 body 占满视窗 + 背景色
    const wrapper = idoc.createElement('div')
    wrapper.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml')
    wrapper.setAttribute(
      'style',
      `width:${width}px;height:${height}px;overflow:hidden;margin:0;padding:0;` +
      `background:${opts.targetTheme === 'dark' ? 'hsl(224 71% 4%)' : 'hsl(0 0% 100%)'};` +
      'transform:translateZ(0);'
    )
    const viewportStyles = window.getComputedStyle(document.documentElement)
    const bg = viewportStyles.getPropertyValue('--background').trim()
    const htmlClone = idoc.documentElement
    htmlClone.style.setProperty('width', width + 'px', 'important')
    htmlClone.style.setProperty('height', height + 'px', 'important')
    htmlClone.style.setProperty('overflow', 'hidden', 'important')
    const body = htmlClone.querySelector('body') as HTMLElement | null
    if (body) {
      body.style.setProperty('width', width + 'px', 'important')
      body.style.setProperty('height', height + 'px', 'important')
      body.style.setProperty('overflow', 'hidden', 'important')
      body.style.setProperty('margin', '0', 'important')
    }
    // 设置 html 类以确保 dark/palette 生效
    htmlClone.classList.remove('dark')
    if (opts.targetTheme === 'dark') htmlClone.classList.add('dark')
    if (opts.palette) {
      for (const cls of Array.from(htmlClone.classList)) {
        if (cls.startsWith('palette-')) htmlClone.classList.remove(cls)
      }
      htmlClone.classList.add(`palette-${opts.palette}`)
    }

    foreignObject.innerHTML = xhtml
    svg.appendChild(foreignObject)

    const svgStr = new XMLSerializer().serializeToString(svg as unknown as Node)
    const svgBlob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(svgBlob)

    const img = new Image()
    img.decoding = 'async'
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('snapshot-img-load-failed'))
      img.src = url
    })

    const canvas = document.createElement('canvas')
    canvas.width = Math.ceil(width * dpr)
    canvas.height = Math.ceil(height * dpr)
    const ctx = canvas.getContext('2d', { willReadFrequently: false })
    if (!ctx) { URL.revokeObjectURL(url); return null }
    // 用 document 中 root 的背景作为兜底填充，避免 cross-origin font / image 不渲染导致大片透明
    ctx.fillStyle = opts.targetTheme === 'dark' ? '#0b1020' : '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.scale(dpr, dpr)
    ctx.drawImage(img, 0, 0, width, height)
    URL.revokeObjectURL(url)

    let dataUrl = ''
    try {
      dataUrl = canvas.toDataURL('image/png')
    } catch (e) {
      // foreignObject 在跨源资源（例如 Google Fonts / remote img）出现时，会把 canvas 污染，
      // toDataURL 抛 SecurityError。此时回退：把画布内容用「SVG + solid background」渲染为一层伪截图。
      dataUrl = fallbackSolidSnapshot(opts.targetTheme, width, height)
    }
    return { dataUrl, width, height }
  } catch (e) {
    return { dataUrl: fallbackSolidSnapshot(opts.targetTheme, w, h), width: w, height: h }
  }
}

function fallbackSolidSnapshot(targetTheme: 'light' | 'dark', width: number, height: number): string {
  const bg = targetTheme === 'dark' ? '#0b1020' : '#ffffff'
  const foreground = targetTheme === 'dark' ? '#cbd5e1' : '#0f172a'
  const canvas = document.createElement('canvas')
  const dpr = Math.min(2, window.devicePixelRatio || 1)
  canvas.width = Math.ceil(width * dpr)
  canvas.height = Math.ceil(height * dpr)
  const ctx = canvas.getContext('2d')
  if (!ctx) return ''
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  // 画一些伪内容扫描线让它看上去像「锁定了一个页面」而不是纯色块
  ctx.fillStyle = foreground
  ctx.globalAlpha = 0.06
  for (let y = 0; y < height; y += 4) {
    ctx.fillRect(0, y * dpr, Math.ceil(width * 0.55 + (y % 160) * 1.2), Math.max(1, Math.round(dpr)))
  }
  ctx.globalAlpha = 1
  return canvas.toDataURL('image/png')
}

/**
 * 优先使用浏览器 View Transition API 包裹主题切换。
 * 若浏览器支持，调用方仅需把「DOM 切换」塞到 updateCallback 内，浏览器会自动做：
 *   ::view-transition-old(根) 保留旧帧截图
 *   ::view-transition-new(根) 显示新帧
 * 二者默认交叉溶解；我们用 CSS 给根加圆形 clip-path 揭示动画，就会得到
 * 「旧页面真实内容 vs 新页面真实内容，以点击点为圆心的圆形扩散/收缩」。
 *   → 这就是用户说的「截图锁定」效果。
 */
export function supportsViewTransition(): boolean {
  if (!import.meta.client) return false
  return !!(document as any).startViewTransition
}

/** 尝试用 View Transition 包裹 fn；成功返回 true，失败返回 false（调用方应走 snapshot 方案） */
export async function withViewTransition(fn: () => void | Promise<void>): Promise<boolean> {
  if (!import.meta.client) return false
  const start = (document as any).startViewTransition as ((fn: () => any) => { finished: Promise<void> }) | undefined
  if (!start) return false
  try {
    const vt = start(fn)
    if (vt && vt.finished && typeof vt.finished.then === 'function') {
      await vt.finished
    } else {
      await new Promise(r => setTimeout(r, 80))
    }
    return true
  } catch {
    return false
  }
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

  const activePaletteClass = (): string | null => {
    if (!import.meta.client) return null
    for (const cls of Array.from(document.documentElement.classList)) {
      if (cls.startsWith('palette-')) return cls.slice('palette-'.length)
    }
    return null
  }

  const takeSnapshotPair = async (fromTheme: ThemeMode, toTheme: ThemeMode) => {
    const palette = activePaletteClass() ?? undefined
    const timeout = (ms: number) => new Promise<null>((r) => setTimeout(() => r(null), ms))
    const [oldShot, newShot] = await Promise.all([
      Promise.race([snapshotThemePage({ targetTheme: fromTheme, palette }), timeout(900)]),
      Promise.race([snapshotThemePage({ targetTheme: toTheme, palette }), timeout(900)])
    ])
    return { oldShot, newShot }
  }

  const toggle = async (origin?: RippleOrigin | MouseEvent | null, fallbackEl?: Element | ComponentPublicInstance | null) => {
    if (!import.meta.client) { if (isDark.value) setLight(); else setDark(); return }
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reducedMotion) { if (isDark.value) setLight(); else setDark(); return }

    const wasDark = isDark.value
    const nextDark = !wasDark
    const fromMode: ThemeMode = wasDark ? 'dark' : 'light'
    const nextMode: ThemeMode = nextDark ? 'dark' : 'light'
    const { cx, cy } = resolveRippleOrigin(origin, fallbackEl)
    const maxRadius = computeRippleRadius(cx, cy)
    const bg = probeAbsoluteBackground()

    // 首选：View Transition API。浏览器自己抓前后帧（相当于原生截图锁定），
    // 我们只需要把圆心和半径写到 --reveal-cx/cy/r 上，CSS ::view-transition-new 会按 circle 揭示。
    // 失败（旧浏览器 / 跨域资源 / 开发者工具打断）则回退：手动 iframe+svg 截图 before/after，走 ripple overlay 两层图。
    const tryVT = async (): Promise<boolean> => {
      if (!supportsViewTransition()) return false
      const root = document.documentElement
      // 把点击坐标写入 CSS 变量，动画从点击位置开始（参考 B 站客户端的圆形揭示）
      root.style.setProperty('--reveal-cx', cx + 'px')
      root.style.setProperty('--reveal-cy', cy + 'px')
      // 切换方向由 html.theme-grow / .theme-shrink 控制（纯 CSS @keyframes 驱动，
      // 避免某些 Chromium 下 ::view-transition-old 上的 JS animate 不播放的已知坑）
      root.classList.remove('theme-grow', 'theme-shrink')
      // 强制 reflow 再 add，避免同一帧内浏览器把两次 class 变更合并导致动画不触发
      void (root as HTMLElement).offsetWidth
      const dirClass = nextDark ? 'theme-grow' : 'theme-shrink'
      root.classList.add(dirClass)
      let ok = true
      try {
        const startVT = (document as any).startViewTransition as ((fn: () => any) => { finished: Promise<void> })
        const vt = startVT(() => {
          applyTheme(nextDark)
          themeMode.value = nextMode
          persist()
        })
        if (vt?.finished && typeof vt.finished.then === 'function') {
          // 用 finished 清理（坑：用 ready 会在动画刚启动就清掉 z-index，瞬间消失）
          vt.finished.then(() => {
            root.classList.remove('theme-grow', 'theme-shrink')
            root.style.removeProperty('--reveal-cx')
            root.style.removeProperty('--reveal-cy')
          }).catch(() => { /* noop */ })
          await vt.finished
        } else {
          await new Promise(r => setTimeout(r, 80))
        }
      } catch {
        ok = false
        root.classList.remove('theme-grow', 'theme-shrink')
        root.style.removeProperty('--reveal-cx')
        root.style.removeProperty('--reveal-cy')
      }
      return ok
    }

    const vtOk = await tryVT()
    if (vtOk) {
      // 浏览器已经把前后帧的截图做了圆形揭示，不需要我们再画 overlay
      return
    }

    // —— 回退：手动做「截图锁定」——
    // 整个动画期间用户看到的屏幕 = 旧主题全屏截图 + 新主题圆形裁剪截图（circle: 0↔R），
    // 底层真实 DOM 在中间时机切换，避免用户看到纯黑/纯白斑驳。
    const { oldShot, newShot } = await takeSnapshotPair(fromMode, nextMode)

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
      beforeImage: oldShot?.dataUrl ?? '',
      afterImage: newShot?.dataUrl ?? '',
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


