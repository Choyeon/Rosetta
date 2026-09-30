/**
 * 客户端主题同步（Hydrate 完成后执行，严格避免 mismatch）：
 *
 *  useTheme().initFromStorageAndApply()
 *     - 读取 localStorage.theme / matchMedia 偏好
 *     - 同时写入共享 useState('theme-dark'/'theme-mode') & <html>.classList
 *     - 因为在 Hydrate 之后执行，Vue 走 patch 流程，ThemeToggle 的 SVG 不会 mismatch
 */
export default defineNuxtPlugin((nuxtApp) => {
  if (!import.meta.client) return

  const runAfterHydrate = () => {
    const { initFromStorageAndApply } = useTheme()
    initFromStorageAndApply()
  }

  // 【为什么用 app:mounted 而不是 window.load】
  // window.load 要等**所有子资源**（图片/字体/iframe）下载完才触发。而 <head> 里的
  // 内联 FOUC 防护脚本已经在文档解析阶段就把 html 的 dark/light class 写好了，
  // 也就是说「背景/文字色」不会闪；真正会闪的是 Vue 控制的那些东西 —— ThemeToggle
  // 的日月图标、用到 theme-dark state 的 Toast 与渐变容器。这些组件其实在
  // app:mounted（Hydration 完成、DOM 已可 patch）那一刻就已经渲染出来了，等到
  // window.load 才纠偏，中间隔着几十到几百毫秒的错色帧：外链字体/图片越慢越明显。
  // 同理，'load' 已经触发过的极端情况（插件延迟注册）仍需 readyState 兜底。
  // initFromStorageAndApply 本身幂等（读 storage → applyTheme → persist），但仍显式
  // 加单次闸门：避免 app:mounted 与 readyState 兜底两条路径都跑时对同一份 state 连写两次。
  let applied = false
  const runOnce = () => {
    if (applied) return
    applied = true
    runAfterHydrate()
  }

  nuxtApp.hook('app:mounted', runOnce)
  // 兜底：插件注册晚于 app:mounted（如延迟 hydrate / 客户端-only 路由切换）时补一次
  if (document.readyState === 'complete') setTimeout(runOnce, 0)
})
