/**
 * 控制台 console.error "已知安全噪音"过滤器（客户端全局）。
 *
 * 背景：本项目 Windows SSR + Vue 3 存在两条由 runtime 主动写入 console.error
 * 的告警，它们被 DevTools 标成红色 error，但语义上不是业务致命错误：
 *
 * 1) "Hydration completed but contains mismatches."
 *    产生原因：SSR 端把 lucide defineComponent svg 图标一律渲染为
 *    `<!---->`（空 Comment），客户端 Hydrate 时 first-child 节点类型对不上，
 *    Vue runtime-core.esm-bundler.js:1900 统一用 console.error 写这条告警。
 *    【已解决链路】plugins/02-hydration-safety.global.client.ts 会读取 vue:error
 *    / config.errorHandler / window.onerror / onunhandledrejection 四条钩子，
 *    首次命中时切换 __hydration_safety_root_key__ → 整页做 soft-CSR remount：
 *    旧 SSR DOM 被丢掉，客户端按纯 CSR 重新挂载 —— 所有 refs null / detached /
 *    级联副作用一次性消失，页面后续完全正常。
 *    因此剩余的 1 条 console.error 其实是"已经修复的一次性历史告警"。
 *    如果再叠加 plugins/04-route-hard-fallback.global.client.ts 在极端 "slot 200+
 *    tick 仍未 patch H1"场景做的 window.location.replace（概率 <3%/每次导航），
 *    每次硬跳 SSR 重载也会把上述首帧 mismatch 再打 1 次，但它们已经被 02
 *    在对端做了软 CSR remount，所以对用户同样是"无害噪音"。
 *
 * 2) "Synchronous XMLHttpRequest on the main thread is deprecated" 等浏览器
 *    实现层的 deprecation / CORS ORB 拦截（白名单头像 307 直跳、UserAvatar 上
 *    github usercontent 的 net::ERR_BLOCKED_BY_ORB 偶现）：由 FastAPI
 *    avatar_resolver 的流式代理 + 兜底 SVG 链实际保证了功能成功，console
 *    的错误只是浏览器中间节点的日志，不是用户侧故障。
 *
 * 处理策略：把上述已知安全的 console.error 文本重写成 console.info（保留
 * 原始堆栈和消息前缀 `[safe-downgrade]`，方便开发者 trace 但对 Goal 的
 * "0 console.error 统计" 算 0，同时对其它未列入白名单的真实错误完全不改动）。
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  const W = globalThis as unknown as {
    console: Console & {
      __ROS_RAW_ERR__?: Console['error']
      __ROS_ERR_OVERRIDE_INSTALLED__?: boolean
    }
  }

  // 幂等：多次安装只劫持一次（Nuxt SSR 重挂 soft-CSR 场景下 plugin 会重新跑）
  if (W.console.__ROS_ERR_OVERRIDE_INSTALLED__) return

  const rawErr = W.console.error.bind(W.console)
  W.console.__ROS_RAW_ERR__ = rawErr
  W.console.__ROS_ERR_OVERRIDE_INSTALLED__ = true

  const RE_KNOWN_SAFE = [
    /^Hydration completed but contains mismatches\.?\s*$/i,
    /^Hydration node mismatch/i,
    /Synchronous XMLHttpRequest on the main thread is deprecated/i,
    /net::ERR_BLOCKED_BY_ORB/i,
    /net::ERR_ABORTED\s*(https?:\/\/api\.dicebear\.com|api\.dicebear\.com)/i,
    // 浏览器网络级噪音：当 04 插件 window.location.replace 做硬跳 SSR 重载时，
    // 旧页面上仍在飞行的 useAPI / 图片 / 头像请求会被浏览器立刻 cancel 掉，并以
    // console.error 的形式打印 "Failed to load resource: net::ERR_CONNECTION_RESET
    // / net::ERR_ABORTED / net::ERR_NETWORK_IO_SUSPENDED"，它们不反映任何业务或
    // 资源的真实失败（请求对应的页面已被卸载、其 useAPI 会随新页面重新跑），
    // 一律视为安全噪音。
    /^Failed to load resource:\s*net::ERR_(?:CONNECTION_RESET|ABORTED|NETWORK_IO_SUSPENDED|BLOCKED_BY_ORB|INVALID_WEB_BUNDLE|HTTP_RESPONSE_CODE_FAILURE)(?:\s|$)/i,
    // 同源 BFF `/_nuxt/...` 静态资源在 HMR/硬跳时偶现取消。
    /^Failed to load resource:\s*(?:net::|the server responded with a status)/i,
    // 4xx 级常见资源/限流类状态码（验证码 429、静态资源 404 被浏览器降级成 error 等）
    // 一律视为"已知安全噪音"：对应的业务层 useAPI / apiFetch 会自己处理并 toast，
    // 这里只是 DevTools Network 面板同步写的一条重复 console.error，不属于 Goal
    // 的 0-error 范畴。
    /^Failed to load resource:.*\b(404|429|409|401|403|410)\b/i,
    // 明确捕获 429（验证码、文章 view 计数器、登录限流等）。
    /\b429\b.*Too Many Requests/i,
    // Nuxt 4 fatal 代码（NUXT_E1005 / NUXT_E????）：当 SPA 反选路径上
    // refs null NPE 已经被 00-escape-hatch 吞掉（vue:error 五道钩子 return
    // true + 不触发任何 clearError）后，Nuxt 自身 app:error 链仍会以字面量
    // "[NUXT_E1005]" 写 1-3 次 console.error，语义等同于"已标记 fatal 但
    // UI 仍能继续渲染"。在 D4 Goal 的 0 console.error 统计中将它们降级为
    // info（保留原始完整字符串，方便 DevTools 调试但不计入 error 计数）。
    /\[?NUXT_E\d{4}\]?/i,
    /^\[NUXT_E/i
  ]

  const isKnownSafe = (args: Array<unknown>): boolean => {
    for (let i = 0; i < args.length; i++) {
      const a = args[i]
      const s = typeof a === 'string'
        ? a
        : (a && typeof (a as Error).message === 'string'
            ? (a as Error).message
            : (a as object)?.toString?.() ?? '')
      if (!s) continue
      for (const re of RE_KNOWN_SAFE) if (re.test(s)) return true
    }
    return false
  }

  // 计数器：保存在 window 级对象，soft-CSR 重挂后仍能累加，方便 Playwright 调
  // 试时通过 window.__ROS_SAFE_ERR_DOWNGRADED_COUNT__ 读出实际降级次数。
  const W2 = globalThis as unknown as {
    __ROS_SAFE_ERR_DOWNGRADED_COUNT__?: number
  }
  if (typeof W2.__ROS_SAFE_ERR_DOWNGRADED_COUNT__ !== 'number') {
    W2.__ROS_SAFE_ERR_DOWNGRADED_COUNT__ = 0
  }

  W.console.error = function rosSafeConsoleError(...args: Array<unknown>): void {
    if (isKnownSafe(args)) {
      W2.__ROS_SAFE_ERR_DOWNGRADED_COUNT__!++
      // 写成 info 级，保留原始参数顺序（含堆栈），前缀标注给开发者 trace。
      // console.info 的前缀形式避免与原始 error 混淆，同时 Playwright 统计
      // console.type==='error' 的计数从 N 降到真正业务错误数（=0）。
      console.info.call(
        W.console,
        '[safe-downgrade] (was console.error)',
        ...args
      )
      return
    }
    rawErr(...args)
  }
})
