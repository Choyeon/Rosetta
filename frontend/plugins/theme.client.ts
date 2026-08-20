import { ALL_PALETTE_CLASSES, DEFAULT_PALETTE } from '~~/composables/useThemePalette'

export default defineNuxtPlugin(() => {
  if (!import.meta.client) return
  const root = document.documentElement

  const stalePaletteClasses: string[] = []
  for (const cls of root.classList) {
    if (cls.startsWith('palette-')) stalePaletteClasses.push(cls)
  }
  for (const cls of stalePaletteClasses) root.classList.remove(cls)

  let isDark: boolean
  try {
    const stored = localStorage.getItem('theme')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDark = stored === 'dark' || (!stored && prefersDark)
  } catch {
    isDark = false
  }
  if (isDark) root.classList.add('dark')
  else root.classList.remove('dark')

  for (const cls of ALL_PALETTE_CLASSES) root.classList.remove(cls)
  root.classList.add(`palette-${DEFAULT_PALETTE}`)

  const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
  if (meta) {
    const bg = getComputedStyle(root).getPropertyValue('--background').trim()
    meta.content = bg ? `hsl(${bg})` : (isDark ? '#0b1020' : '#ffffff')
  }
})
