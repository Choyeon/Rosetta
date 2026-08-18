/**
 * Rosetta 全局主题管理（与 ThemeToggle.vue / theme.client.ts 保持一致）
 * 存储规范（与 project_memory.md 对齐）：
 *   localStorage.theme 只能存 'light' | 'dark'
 *   旧值 'system' / 'rosetta-theme' 会在 init 时迁移为当前系统主题对应的值
 */
const STORAGE_KEY = 'theme'
type ThemeMode = 'light' | 'dark'

export function useTheme() {
  const isDark = ref(false)
  const themeMode = ref<ThemeMode>('light')

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
      // 同步 meta[name=theme-color]，避免移动端浏览器 chrome 颜色衔接闪屏
      const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
      if (meta) {
        const bg = getComputedStyle(root).getPropertyValue('--background').trim()
        meta.content = bg ? `hsl(${bg})` : (dark ? '#0b1020' : '#ffffff')
      }
    }
    isDark.value = dark
  }

  const persist = () => {
    if (import.meta.client && typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, themeMode.value)
      // 清理旧的存储 key，避免冲突（project_memory 规定只用 theme）
      try { localStorage.removeItem('rosetta-theme') } catch { /* noop */ }
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
    if (isDark.value) {
      setLight()
    } else {
      setDark()
    }
  }

  const init = () => {
    if (!import.meta.client) return

    try {
      // 迁移旧值：'system' → 根据系统偏好解析；rosetta-theme key → 同步到 theme 并删除
      const legacy = localStorage.getItem('rosetta-theme')
      let stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | string | null

      if (!stored && legacy) {
        stored = legacy
      }

      if (stored === 'dark') {
        themeMode.value = 'dark'
      } else if (stored === 'light') {
        themeMode.value = 'light'
      } else {
        // 'system' / 空 / 其他非法值：按系统偏好映射（只存 light or dark）
        themeMode.value = getSystemDark() ? 'dark' : 'light'
      }
    } catch {
      themeMode.value = getSystemDark() ? 'dark' : 'light'
    }

    applyTheme(themeMode.value === 'dark')
    persist()
  }

  init()

  return {
    isDark,
    toggle,
    setLight,
    setDark
  }
}
