import { DEFAULT_PALETTE } from '~~/composables/useThemePalette'

/**
 * 客户端主题同步（Hydrate 完成后执行，严格避免 mismatch）：
 *
 *  1. useTheme().initFromStorageAndApply()
 *     - 读取 localStorage.theme / matchMedia 偏好
 *     - 同时写入 共享 useState('theme-dark'/'theme-mode') & <html>.classList
 *     - 因为在 Hydrate 之后执行，Vue 走 patch 流程，ThemeToggle 的 SVG 不会 mismatch
 *
 *  2. palette（当前只支持 'sky'，兼容以后扩展）
 *     - <html class="palette-sky"> 与 SSR 输出一致
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  const paletteState = useState<string>('theme-palette', () => DEFAULT_PALETTE)

  // 读取 palette（兼容以后扩展；当前版本强制为 DEFAULT_PALETTE = 'sky'）
  try {
    const storedPalette = localStorage.getItem('rosetta.palette')
    if (storedPalette) paletteState.value = storedPalette
  } catch { /* storage/palette 读取失败降级使用默认 palette，无需告警 */ }

  const runAfterHydrate = () => {
    // —— 主题（dark/light）：委托给 useTheme 统一处理 —— //
    const { initFromStorageAndApply } = useTheme()
    initFromStorageAndApply()

    // —— palette：打 class 到 <html>（与 SSR 输出一致，避免 mismatch）—— //
    const root = document.documentElement
    const targetPalette = paletteState.value
    const hasPaletteClass = Array.from(root.classList).some(c => c.startsWith('palette-'))
    if (!hasPaletteClass || !root.classList.contains(`palette-${targetPalette}`)) {
      root.classList.forEach((cls) => {
        if (cls.startsWith('palette-')) root.classList.remove(cls)
      })
      root.classList.add(`palette-${targetPalette}`)
    }

    // theme-color meta 会被 useTheme.applyTheme() 里的 syncMetaThemeColor 覆盖，这里不需要
  }

  // 关键：延迟到 load 之后（即 Vue Hydrate 一定完成）再执行
  if (document.readyState === 'complete') setTimeout(runAfterHydrate, 0)
  else window.addEventListener('load', runAfterHydrate, { once: true })
})
