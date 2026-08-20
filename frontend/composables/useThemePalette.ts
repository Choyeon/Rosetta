export type PaletteId = 'sky'

export interface PaletteDefinition {
  id: PaletteId
  name: string
  label: string
  swatch: string
  metaLight: string
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
  }
]

export const DEFAULT_PALETTE: PaletteId = 'sky'
export const PALETTE_STORAGE_KEY = 'rosetta.palette'
export const ALL_PALETTE_CLASSES = PALETTES.map(p => `palette-${p.id}`)

export const isPaletteId = (v: unknown): v is PaletteId => v === DEFAULT_PALETTE

export const migrateStoredPalette = (): PaletteId => DEFAULT_PALETTE

export const useThemePalette = () => {
  const palette = useState<PaletteId>('theme-palette', () => DEFAULT_PALETTE)

  const findPalette = (id: PaletteId): PaletteDefinition =>
    PALETTES.find(p => p.id === id) ?? (PALETTES[0] as PaletteDefinition)

  const applyPalette = (_id: PaletteId) => {
    if (!import.meta.client) return
    const def = findPalette(DEFAULT_PALETTE)
    const root = document.documentElement
    const staleClasses: string[] = []
    for (const cls of root.classList) {
      if (cls.startsWith('palette-')) staleClasses.push(cls)
    }
    for (const cls of staleClasses) root.classList.remove(cls)
    for (const cls of ALL_PALETTE_CLASSES) root.classList.remove(cls)
    root.classList.add(`palette-${def.id}`)
    palette.value = def.id

    const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
    if (meta) {
      const isDark = root.classList.contains('dark')
      const bg = getComputedStyle(root).getPropertyValue('--background').trim()
      meta.content = bg ? `hsl(${bg})` : (isDark ? def.metaDark : def.metaLight)
    }

    try {
      localStorage.setItem(PALETTE_STORAGE_KEY, def.id)
    } catch {
      /* ignore storage errors */
    }
  }

  const hydratePalette = () => {
    applyPalette(DEFAULT_PALETTE)
  }

  return {
    palette,
    palettes: readonly(PALETTES),
    applyPalette,
    hydratePalette,
    findPalette
  }
}
