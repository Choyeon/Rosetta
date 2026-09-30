/**
 * plugins/02-hydration-safety.global.client.ts
 *
 * 最小且诚实的水合防御（frontend/AGENTS.md 允许的唯一定位：只在真实抛错时软重挂）：
 *   命中真实 hydration 级联错误 → 先 console.error 上报，再做有界软重挂
 *   （app.vue 根子树 :key++ 整棵转纯 CSR 重挂，每个文档硬上限 2 次，绝不循环）。
 *
 * 已拆除（原 00-escape-hatch / 旧版 02 / 05-downgrade 的掩盖层，勿再加回）：
 *   · 改写 window.__NUXT_DATA__.serverRendered —— nuxt/dist/app/entry.js 在
 *     applyPlugins() **之前**就用它决定 hydrate/mount，插件期改写是 no-op；
 *     真正生效的是 server/plugins/spa-serverrendered-zero.nitro.ts（HTTP 层）。
 *   · requestIdleCallback 轮询遍历组件实例树、包装 Vue 内置 ref 指令、
 *     eval('clearError')、按消息子串吞 window.onerror / preventDefault
 *     unhandledrejection —— 全部为欺骗性掩盖（window.onerror 覆写实际还会被
 *     error-handler.client.ts 直接赋值冲掉，本就不是可靠拦截点）。
 *
 * 真实根因修复点（都在构建/服务端层）：
 *   · vite `rosetta-lucide-ssr-fix`（SSR lucide 图标 first-child 与客户端同构，消除 mismatch 源）
 *   · vite `rosetta-vue-setref-nullsafe`（Vue setRef 父链 null-safe，见 nuxt.config.ts）
 *   · nitro `spa-serverrendered-zero`（ssr:false 空壳页不再进 hydrate 分支）
 *   · app.pageTransition 不再使用 mode:'out-in'（SSR 首帧 Comment 占位 mismatch 源）
 */
export default defineNuxtPlugin((nuxtApp) => {
  if (!import.meta.client) return

  // ====== app:mounted 已触发标记（stores/auth.initialize 时序依赖）======
  // 2026-10-01 实证（生产构建 + probe 生命周期追踪）：Nuxt entry 在
  // `vueApp.mount()` 返回后立刻 callHook('app:mounted')，但生产构建里根
  // Suspense（异步 layout/page chunk）resolve 晚于该 callHook —— 组件级
  // onMounted（app.vue / layouts / pages）全部在 callHook 之后才跑。
  // 若 initialize() 首次调用发生在组件 onMounted（无 auth 中间件的公开页），
  // 它再注册 app:mounted 监听就永远等不到 → 登录态恢复死锁（生产全站
  // hydrated=null，用户刷新后全部被登出）。
  // 这里在插件阶段（早于 mount）注册一次 hookOnce，把「app:mounted 是否
  // 已错过」暴露给 auth.initialize() 做判定。
  nuxtApp.hooks.hookOnce('app:mounted', () => {
    ;(window as unknown as { __ROSETTA_APP_MOUNTED__?: boolean }).__ROSETTA_APP_MOUNTED__ = true
  })

  const rootKey = useState<number>('__hydration_safety_root_key__', () => 0)

  // WHY 硬上限：历史上无上限的 rootKey++ 循环曾把每次导航变成 30~80 次重挂
  // 打满后端限流；预算耗尽后必须让错误真实暴露，而不是继续"抢救"。
  const MAX_SOFT_REMOUNTS = 2

  // WHY 按消息子串识别：Vue/Nuxt 对这类运行时级联 TypeError 没有错误码字段，
  // 只能在 message 层面判定；判定收窄到 hydration/mismatch/refs-null 三类。
  const isHydrationCascade = (e: unknown): boolean => {
    if (!e) return false
    const msg = (e as Error)?.message ?? String(e)
    if (!msg) return false
    const lc = msg.toLowerCase()
    return (
      lc.includes('hydration')
      || lc.includes('mismatch')
      || msg.includes('reading refs')
      || (lc.includes('null') && lc.includes('refs'))
    )
  }

  const recoverOnce = (ctx: string, err: unknown): void => {
    if (rootKey.value >= MAX_SOFT_REMOUNTS) {
      console.error(`[hydration-safety] ${ctx}: remount budget exhausted, surfacing error as-is`, err)
      return
    }
    console.error(`[hydration-safety] ${ctx}: hydration cascade → soft CSR remount ${rootKey.value + 1}/${MAX_SOFT_REMOUNTS}`, err)
    rootKey.value++
  }

  // 只订阅 vue:error 并仅做有界重挂。app:error 意味着错误已被 Nuxt 判为 fatal
  // 并挂载 error.vue —— App 树此刻已整体 unmount，rootKey++ 救不回来，
  // 正确的诚实路径是让 500 兜底页可见（自带重试按钮），不做 clearError 复活术。
  nuxtApp.hook('vue:error', (err) => {
    if (isHydrationCascade(err)) recoverOnce('vue:error', err)
  })
})
