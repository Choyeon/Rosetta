export type PaletteId = 'indigo' | 'emerald' | 'amber' | 'rose' | 'violet' | 'sky'

export interface PaletteDefinition {
  id: PaletteId
  /** English code name */
  name: string
  /** User-visible label (zh default) */
  label: string
  /** Swatch color for the picker circle button (light-mode primary solid) */
  swatch: string
  /** Suggested browser bar color in light mode (matches --primary fallback) */
  metaLight: string
  /** Suggested browser bar color in dark mode */
  metaDark: string
}

export const PALETTES: PaletteDefinition[] = [
  {
    id: 'sky',
    name: 'Sky',
    label: '天青',
    swatch: 'hsl(201 96% 52%)',
    metaLight: '#ffffff',
    metaDark: '#0b1020'
  },
  {
    id: 'indigo',
    name: 'Indigo',
    label: '靛青',
    swatch: 'hsl(262 83% 58%)',
    metaLight: '#ffffff',
    metaDark: '#0b1020'
  },
  {
    id: 'emerald',
    name: 'Emerald',
    label: '翡翠',
    swatch: 'hsl(158 64% 46%)',
    metaLight: '#ffffff',
    metaDark: '#0b1020'
  },
  {
    id: 'violet',
    name: 'Violet',
    label: '紫罗兰',
    swatch: 'hsl(271 91% 65%)',
    metaLight: '#ffffff',
    metaDark: '#0b1020'
  },
  {
    id: 'rose',
    name: 'Rose',
    label: '玫瑰',
    swatch: 'hsl(346 77% 60%)',
    metaLight: '#ffffff',
    metaDark: '#0b1020'
  },
  {
    id: 'amber',
    name: 'Amber',
    label: '琥珀',
    swatch: 'hsl(42 96% 55%)',
    metaLight: '#ffffff',
    metaDark: '#0b1020'
  }
]

export const DEFAULT_PALETTE: PaletteId = 'sky'
export const PALETTE_STORAGE_KEY = 'rosetta.palette'
export const ALL_PALETTE_CLASSES = PALETTES.map(p => `palette-${p.id}`)

// Palette id validity guard
export const isPaletteId = (v: unknown): v is PaletteId =>
  typeof v === 'string' && PALETTES.some(p => p.id === v)

export const useThemePalette = () => {
  const palette = useState<PaletteId>('theme-palette', () => DEFAULT_PALETTE)

  const findPalette = (id: PaletteId): PaletteDefinition =>
    PALETTES.find(p => p.id === id) ?? (PALETTES[0] as PaletteDefinition)

  /** Apply palette CSS class to <html> and update meta[name="theme-color"] */
  const applyPalette = (id: PaletteId) => {
    if (!import.meta.client) return
    const def = findPalette(id)
    const root = document.documentElement
    // strip any previous palette class
    for (const cls of ALL_PALETTE_CLASSES) root.classList.remove(cls)
    root.classList.add(`palette-${def.id}`)
    palette.value = def.id

    // Update browser chrome theme-color if meta exists
    const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
    if (meta) {
      const isDark = root.classList.contains('dark')
      const bg = getComputedStyle(root).getPropertyValue('--background').trim()
      meta.content = bg ? `hsl(${bg})` : (isDark ? def.metaDark : def.metaLight)
    }

    try {
      localStorage.setItem(PALETTE_STORAGE_KEY, def.id)
    } catch {
      /* ignore storage errors (e.g. private mode) */
    }
  }

  /** Load persisted palette from localStorage and apply it once on hydration */
  const hydratePalette = () => {
    if (!import.meta.client) return
    let id: PaletteId = DEFAULT_PALETTE
    try {
      const raw = localStorage.getItem(PALETTE_STORAGE_KEY)
      if (isPaletteId(raw)) id = raw
    } catch { /* noop */ }
    applyPalette(id)
  }

  return {
    palette,
    palettes: readonly(PALETTES),
    applyPalette,
    hydratePalette,
    findPalette
  }
}
