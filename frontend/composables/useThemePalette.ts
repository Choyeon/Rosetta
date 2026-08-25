/**
 * Rosetta 调色板（palette / 皮肤）管理
 *
 * 调色板是在明暗模式之上叠的一层「品牌色皮肤」。明暗决定语义变量的深/浅取值，
 * 调色板决定 --primary / --accent / --ring / --sidebar-primary 等品牌相关变量取哪个色相。
 * 两层互相独立：<html class="dark palette-violet"> 这种组合是合法的。
 *
 * 设计要点（对照 WordPress 的 theme mod）：
 *   - 调色板清单 PALETTES 是「前端已知的可选项」，与 assets/css/main.css 里的
 *     html.palette-* 块一一对应（改 CSS 必须同步改这里，反之亦然）。
 *   - 真实启用的调色板由「用户本地选择（localStorage.rosetta.palette）」或
 *     「后端站点 theme_key」决定，前端不写死默认之外的强制逻辑。
 *   - applyPalette(id) 真正把 id 落到 <html>.classList 上，不再写死 DEFAULT_PALETTE。
 *
 * 存储：localStorage.rosetta.palette 存 palette id（如 'violet'）；非法值回退 DEFAULT_PALETTE。
 */

export type PaletteId =
  | 'sky'
  | 'indigo'
  | 'emerald'
  | 'amber'
  | 'rose'
  | 'violet'
  | 'warm-stone'
  | 'minimal'

export interface PaletteDefinition {
  id: PaletteId
  name: string
  label: string
  /** 浅色模式下的主色 swatch（用于切换器小圆点预览） */
  swatch: string
  /** 浅色模式下 theme-color meta 取值 */
  metaLight: string
  /** 深色模式下 theme-color meta 取值 */
  metaDark: string
}

/**
 * 与 frontend/assets/css/main.css 中 html.palette-* 块一一对应。
 * swatch 取该调色板浅色 --primary 的近似 hex，供 UI 预览。
 */
export const PALETTES: PaletteDefinition[] = [
  {
    id: 'sky',
    name: 'Sky',
    label: '天青',
    swatch: 'hsl(201 96% 52%)',
    metaLight: '#eaf4ff',
    metaDark: '#0b1020'
  },
  {
    id: 'indigo',
    name: 'Indigo',
    label: '靛蓝',
    swatch: 'hsl(262 83% 58%)',
    metaLight: '#f1ecff',
    metaDark: '#0e0a1f'
  },
  {
    id: 'emerald',
    name: 'Emerald',
    label: '翠绿',
    swatch: 'hsl(158 64% 46%)',
    metaLight: '#e8f8f0',
    metaDark: '#06140f'
  },
  {
    id: 'amber',
    name: 'Amber',
    label: '琥珀',
    swatch: 'hsl(42 96% 55%)',
    metaLight: '#fff6e0',
    metaDark: '#1a1206'
  },
  {
    id: 'rose',
    name: 'Rose',
    label: '玫瑰',
    swatch: 'hsl(346 77% 60%)',
    metaLight: '#ffeef3',
    metaDark: '#1a0a0f'
  },
  {
    id: 'violet',
    name: 'Violet',
    label: '紫罗兰',
    swatch: 'hsl(271 91% 65%)',
    metaLight: '#f6efff',
    metaDark: '#120a1a'
  },
  {
    id: 'warm-stone',
    name: 'Warm Stone',
    label: '赭石',
    swatch: 'hsl(32 94% 44%)',
    metaLight: '#fbf1e3',
    metaDark: '#140d05'
  },
  {
    id: 'minimal',
    name: 'Minimal',
    label: '极简',
    swatch: 'hsl(220 9% 46%)',
    metaLight: '#fafafa',
    metaDark: '#0a0a0a'
  }
]

export const DEFAULT_PALETTE: PaletteId = 'sky'
export const PALETTE_STORAGE_KEY = 'rosetta.palette'
export const ALL_PALETTE_CLASSES = PALETTES.map((p) => `palette-${p.id}`)

const VALID_IDS = new Set<string>(PALETTES.map((p) => p.id))

export const isPaletteId = (v: unknown): v is PaletteId =>
  typeof v === 'string' && VALID_IDS.has(v)

/** 把任意存储值规范化为合法 PaletteId，非法/缺省回退默认 */
export const migrateStoredPalette = (v: unknown): PaletteId =>
  isPaletteId(v) ? v : DEFAULT_PALETTE

export const useThemePalette = () => {
  const palette = useState<PaletteId>('theme-palette', () => DEFAULT_PALETTE)

  const findPalette = (id: PaletteId): PaletteDefinition =>
    PALETTES.find((p) => p.id === id) ?? (PALETTES[0] as PaletteDefinition)

  /**
   * 把调色板落到 <html>.classList，并同步 theme-color meta。
   * 真正使用传入的 id（不再写死 DEFAULT_PALETTE）。
   * 在 SSR 阶段也可被调用（此时 document 不存在，只更新 state，class 由 Nuxt 插件处理）。
   */
  const applyPalette = (id: PaletteId) => {
    const safeId = migrateStoredPalette(id)
    palette.value = safeId

    if (!import.meta.client || typeof document === 'undefined') return

    const root = document.documentElement
    const staleClasses: string[] = []
    for (const cls of Array.from(root.classList)) {
      if (cls.startsWith('palette-')) staleClasses.push(cls)
    }
    for (const cls of staleClasses) root.classList.remove(cls)
    root.classList.add(`palette-${safeId}`)

    const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
    if (meta) {
      const isDark = root.classList.contains('dark')
      const def = findPalette(safeId)
      meta.content = isDark ? def.metaDark : def.metaLight
    }

    try {
      localStorage.setItem(PALETTE_STORAGE_KEY, safeId)
    } catch {
      /* ignore storage errors */
    }
  }

  /**
   * 客户端 hydrate 后调用：读取 localStorage 里用户上次选的调色板并应用。
   * 与 useTheme().initFromStorageAndApply 配对，由 plugins/theme.client.ts 在 hydrate 后调用。
   */
  const hydratePalette = () => {
    if (!import.meta.client) return
    let stored: string | null = null
    try {
      stored = localStorage.getItem(PALETTE_STORAGE_KEY)
    } catch {
      stored = null
    }
    applyPalette(migrateStoredPalette(stored ?? DEFAULT_PALETTE))
  }

  return {
    palette,
    palettes: readonly(PALETTES),
    applyPalette,
    hydratePalette,
    findPalette,
    isPaletteId,
    migrateStoredPalette
  }
}
