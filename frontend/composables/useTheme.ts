const STORAGE_KEY = 'rosetta-theme'
type ThemeMode = 'light' | 'dark' | 'system'

export function useTheme() {
  const isDark = ref(false)
  const themeMode = ref<ThemeMode>('system')

  const getSystemDark = () => {
    if (import.meta.client && typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return false
  }

  const applyTheme = (dark: boolean) => {
    if (import.meta.client && typeof document !== 'undefined') {
      const root = document.documentElement
      if (dark) {
        root.classList.add('dark')
      } else {
        root.classList.remove('dark')
      }
    }
    isDark.value = dark
  }

  const resolveDark = () => {
    if (themeMode.value === 'system') {
      return getSystemDark()
    }
    return themeMode.value === 'dark'
  }

  const persist = () => {
    if (import.meta.client && typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, themeMode.value)
    }
  }

  const setLight = () => {
    themeMode.value = 'light'
    applyTheme(false)
    persist()
  }

  const setDark = () => {
    themeMode.value = 'dark'
    applyTheme(true)
    persist()
  }

  const toggle = () => {
    const currentDark = resolveDark()
    if (currentDark) {
      setLight()
    } else {
      setDark()
    }
  }

  const init = () => {
    if (!import.meta.client) return

    try {
      const stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | null
      if (stored === 'light' || stored === 'dark' || stored === 'system') {
        themeMode.value = stored
      } else {
        themeMode.value = 'system'
      }
    } catch {
      themeMode.value = 'system'
    }

    applyTheme(resolveDark())

    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = () => {
        if (themeMode.value === 'system') {
          applyTheme(mediaQuery.matches)
        }
      }
      if (typeof mediaQuery.addEventListener === 'function') {
        mediaQuery.addEventListener('change', handleChange)
      } else if (typeof mediaQuery.addListener === 'function') {
        mediaQuery.addListener(handleChange)
      }
    }
  }

  init()

  return {
    isDark,
    toggle,
    setLight,
    setDark
  }
}
