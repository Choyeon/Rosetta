/**
 * Hydration 防御插件（客户端全局）
 *
 * 根因（本项目 Windows SSR 环境）：
 * 任何 Vue defineComponent 形式的 svg 图标组件（无论 @lucide/vue 还是自建 h()），SSR 端一律
 * 渲染为 `<!---->` 空 Comment；客户端 Hydrate 时 first-child 类型不匹配 → Vue 拆 SSR DOM
 * 重建子树 → 子组件 instance 指针 detached → 级联 refs null TypeError。
 *
 * 本插件提供"最后一道防线"（不替代根因修复）：
 *   1. 静默吞掉 Hydration mismatch 警告 + refs null 级联错误（不打扰用户）。
 *   2. 首次触发 Hydration 级联错误时，将整页切为纯 CSR（切换 #__nuxt 根 key），
 *      让客户端重新走正常挂载，避免后续任何 detached 副作用。
 */
export default defineNuxtPlugin((nuxtApp) => {
  if (!import.meta.client) return

  const rootKey = useState<number>('__hydration_safety_root_key__', () => 0)
  let recovered = false

  const isHydrationError = (e: unknown): boolean => {
    if (!e) return false
    const msg = (e as Error)?.message ?? String(e)
    if (!msg) return false
    const lc = msg.toLowerCase()
    return (
      lc.includes('hydration')
      || lc.includes('mismatch')
      || msg.includes('reading refs')
      || msg.includes('reading refs')
      || (lc.includes('null') && lc.includes('refs'))
    )
  }

  const SPA_REDIRECT_PATHS = new Set([
    '/login',
    '/register',
    '/oobe',
    '/search'
  ])
  const isSpaPath = (): boolean => {
    try {
      const p = location.pathname
      if (SPA_REDIRECT_PATHS.has(p)) return true
      if (p.startsWith('/admin/') || p === '/admin') return true
      if (p.startsWith('/search/')) return true
    } catch {
      /* guard: location access can throw inside sandboxed error recovery */
    }
    return false
  }

  const onFatal = (ctx: string) => {
    if (recovered) return
    recovered = true

    // ssr:false 精准反选路径（登录/注册/OOBE/搜索/管理端）特殊处理：
    // 这些路径在 Nitro node-server standalone 下，SSR 层输出的 body 几乎是
    // 空壳（只有 #__nuxt 空 div），客户端 Hydrate 时 instance.refs === null
    // 会立刻判成 Hydration 级联错 → onFatal → rootKey++ 软 CSR 重挂 →
    // 第二次重挂时 Nuxt 仍然无法找到对应 DOM → 再次级联报错 → error.vue 500
    // 冒泡"Cannot read properties of null (reading 'refs')"。
    //
    // 既然这些路径已经明确 ssr:false，它们本就应当走纯客户端挂载；一旦
    // 命中 refs null，直接把 location.replace 到自己 → 一次性让客户端按
    // 纯 SPA bootstrap，不再在根 key 上做软 CSR 重挂循环。
    if (isSpaPath()) {
      const target = location.pathname + location.search + location.hash
      console.info(
        `[hydration-safety] ${ctx} SPA detected(${location.pathname}) → soft client bootstrap via navigateTo(${target})`
      )
      // ssr:false 空壳页面：不要 window.location.replace（同路径硬跳会再次命中
      // 空壳 → 再次 refs null → 死循环 500）。改成 navigateTo + replace:true
      // + force 让客户端走纯 CSR 的导航解析，Vue 会把 shell 当成纯 SPA 重
      // 新挂载，没有任何 SSR DOM 需要对齐 → refs 级联不再触发。
      try {
        const nuxt = useNuxtApp()
        const maybePromise = nuxt.callHook('page:loading:start') as unknown as Promise<void> | void
        if (typeof maybePromise === 'object' && maybePromise && typeof (maybePromise as Promise<void>).catch === 'function') {
          (maybePromise as Promise<void>).catch(() => {})
        }
        // 同样微任务先出栈，确保剩余同批错误钩子执行完（此时 recovered=true
        // 已经短路 onFatal 重入）。
        setTimeout(() => {
          nuxt.$router?.replace?.(target)
          if (!nuxt.$router) {
            // 极个别 Nitro standalone 场景下 useNuxtApp 取到实例但 $router
            // 尚未挂载，退化成 navigateTo composable。
            try {
              navigateTo(target, { replace: true, open: undefined } as Record<string, unknown> as Parameters<typeof navigateTo>[1])
            } catch {
              /* ignore */
            }
          }
        }, 10)
      } catch {
        // 极端：nuxt 实例拿不到，退化成软 key++（仍然可能 500，但概率极低）。
        setTimeout(() => {
          rootKey.value++
        }, 10)
      }
      return
    }

    console.info(`[hydration-safety] ${ctx} detected → soft-CSR remount (rootKey++)`)
    rootKey.value++
  }

  // Nuxt 层面：vue:app:error / vue:error 双钩子拦截
  nuxtApp.hook('vue:error', (err) => {
    if (isHydrationError(err)) {
      onFatal('vue:error')
    }
  })

  // App.config.errorHandler（不吞非 Hydration 错误）
  const origHandler = nuxtApp.vueApp.config.errorHandler
  nuxtApp.vueApp.config.errorHandler = (err, instance, info) => {
    if (isHydrationError(err)) {
      onFatal('config.errorHandler')
      return
    }
    if (origHandler) origHandler.call(nuxtApp.vueApp, err as Error, instance, info)
  }

  // window.onerror：拦截控制台第 4 条
  const origOnerror = window.onerror
  window.onerror = function rosHydrationOnError(...args) {
    const [msg, , , , err] = args
    if (isHydrationError(err ?? msg)) {
      onFatal('window.onerror')
      return true // 吞掉
    }
    return origOnerror ? origOnerror.apply(window, args as unknown as Parameters<typeof origOnerror>) : false
  }

  // window.onunhandledrejection：拦截第 2 条
  const origReject = window.onunhandledrejection
  window.onunhandledrejection = function rosHydrationReject(...args) {
    const reason = args[0]?.reason
    if (isHydrationError(reason)) {
      onFatal('unhandledrejection')
      args[0]?.preventDefault?.()
      return
    }
    return origReject ? origReject.apply(window, args) : undefined
  }

  // ——————————————————————————————————————————————————————————————————————
  // NOTE (D2 零级联优化): 原先的 app:mounted "若 DOM 没 svg → 必 mismatch 过 → CSR 重挂"
  // 会在 soft CSR remount（vue:error 触发 rootKey++）完成后的第二次 mounted 再误判：
  //   client 渲染路径下，<svg lucide-icon /> 组件是异步首帧渲染的，mounted 时 DOM 仍无
  //   任何 svg → 再次误判 → 第二次 onFatal rootKey++ → Nuxt 同步 re-sync 导航到同 path →
  //   04 号硬兜底插件 "before path = after path = '/' 且 h1 还没挂上" → 触发
  //   window.location.replace('/') → 死循环 30~80 次直到后端 /api/config /oobe/status
  //   打满 429 → 用户控制台 300+ 条红 error。
  // 保留 vue:error / config.errorHandler / window.onerror / unhandledrejection 四钩子就够了，
  // 真正的 Hydration 级联错误一定会抛到这些钩子。
  // ——————————————————————————————————————————————————————————————————————
})
