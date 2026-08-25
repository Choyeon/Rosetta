import { useThemePalette } from '~~/composables/useThemePalette'

/**
 * 客户端主题同步（Hydrate 完成后执行，严格避免 mismatch）：
 *
 *  1. useTheme().initFromStorageAndApply()
 *     - 读取 localStorage.theme / matchMedia 偏好
 *     - 同时写入 共享 useState('theme-dark'/'theme-mode') & <html>.classList
 *     - 因为在 Hydrate 之后执行，Vue 走 patch 流程，ThemeToggle 的 SVG 不会 mismatch
 *
 *  2. palette（多调色板，与 main.css html.palette-* 一一对应）
 *     - <html class="palette-<key>"> 由 useThemePalette().hydratePalette() 统一处理
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  const { palette, hydratePalette } = useThemePalette()

  const runAfterHydrate = () => {
    // —— 主题（dark/light）：委托给 useTheme 统一处理 —— //
    const { initFromStorageAndApply } = useTheme()
    initFromStorageAndApply()

    // —— palette：读取 localStorage 并真正 apply 到 <html> —— //
    hydratePalette()
  }

  // 关键：延迟到 load 之后（即 Vue Hydrate 一定完成）再执行
  if (document.readyState === 'complete') setTimeout(runAfterHydrate, 0)
  else window.addEventListener('load', runAfterHydrate, { once: true })

  // 暴露当前 palette 给其它插件/组件读取（只读）
  return {
    provide: {
      themePalette: {
        get current() {
          return palette.value
        }
      }
    }
  }
})
