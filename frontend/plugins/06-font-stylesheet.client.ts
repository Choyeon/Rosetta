/**
 * 把 nuxt.config head 里的字体 preload 链接切换为真正的样式表。
 *
 * 首屏 HTML 只带 <link rel="preload" as="style">，所以 Google Fonts 可达与否
 * 都不阻塞渲染；这里在客户端把 rel 改成 stylesheet，浏览器会直接复用
 * preload 已下载好的响应（不会产生第二次请求）。
 *
 * ⚠️ 为什么要在 app:mounted 后再兜底轮询（2026-10-01 实证）：
 * nuxt.config 的 head 配置在 hydration 时由 unhead 重新应用，会把内联双 rAF
 * 脚本已切好的 rel=stylesheet **patch 回 rel=preload**；而本插件最初挂在
 * plugin 阶段执行，早于 unhead 的 patch —— 结果页面上残留一个永远没人消费的
 * preload，Chrome 数秒后必报 "was preloaded using link preload but not used"，
 * 每次整页加载各报一次。策略：插件立即切一次（覆盖无 patch 的场景），
 * app:mounted 后再切一次，并以 200ms 间隔短轮询 4s 兜底 unhead 的晚到 patch。
 */
const switchFontPreloads = () => {
  document.querySelectorAll<HTMLLinkElement>('link[rel="preload"][as="style"]').forEach((link) => {
    link.rel = 'stylesheet'
  })
}

export default defineNuxtPlugin(() => {
  switchFontPreloads()

  if (!import.meta.client) return
  const nuxtApp = useNuxtApp()
  nuxtApp.hooks.hookOnce('app:mounted', () => {
    switchFontPreloads()
    let ticks = 0
    const timer = setInterval(() => {
      switchFontPreloads()
      // 连续若干轮都没有 preload 残留即提前收工；最多 20 轮（4s）硬停
      const left = document.querySelectorAll('link[rel="preload"][as="style"]').length
      ticks++
      if (left === 0 && ticks >= 5) clearInterval(timer)
      if (ticks >= 20) clearInterval(timer)
    }, 200)
  })
})
