/**
 * 客户端主题同步（Hydrate 完成后执行，严格避免 mismatch）：
 *
 *  useTheme().initFromStorageAndApply()
 *     - 读取 localStorage.theme / matchMedia 偏好
 *     - 同时写入共享 useState('theme-dark'/'theme-mode') & <html>.classList
 *     - 因为在 Hydrate 之后执行，Vue 走 patch 流程，ThemeToggle 的 SVG 不会 mismatch
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  const runAfterHydrate = () => {
    const { initFromStorageAndApply } = useTheme()
    initFromStorageAndApply()
  }

  if (document.readyState === 'complete') setTimeout(runAfterHydrate, 0)
  else window.addEventListener('load', runAfterHydrate, { once: true })
})
