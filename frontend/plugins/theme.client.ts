// Client-only plugin: apply persisted dark-mode + palette ASAP to avoid FOUC
// (runs before component onMounted hooks that hydrate the same state)
import { PALETTE_STORAGE_KEY, ALL_PALETTE_CLASSES, DEFAULT_PALETTE, isPaletteId } from '~~/composables/useThemePalette'

export default defineNuxtPlugin(() => {
  if (!import.meta.client) return
  const root = document.documentElement

  // --- 1) Dark / light mode ---
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

  // --- 2) Color palette (brand tint) ---
  let palette: string = DEFAULT_PALETTE
  try {
    const raw = localStorage.getItem(PALETTE_STORAGE_KEY)
    if (isPaletteId(raw)) palette = raw
  } catch { /* noop */ }
  for (const cls of ALL_PALETTE_CLASSES) root.classList.remove(cls)
  root.classList.add(`palette-${palette}`)

  // --- 3) theme-color meta for mobile browser chrome ---
  const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
  if (meta) {
    const bg = getComputedStyle(root).getPropertyValue('--background').trim()
    meta.content = bg ? `hsl(${bg})` : (isDark ? '#0b1020' : '#ffffff')
  }
})
