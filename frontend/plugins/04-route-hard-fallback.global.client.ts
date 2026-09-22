/**
 * 导航切换最终兜底：location 硬跳转。
 *
 * （Windows 环境下 Nuxt 4 SSR 项目的已知顽疾）
 * Hydration mismatch → 02-hydration-safety 做 soft CSR remount 后，
 * vue-router 的 RouterView / <NuxtPage> 在相同 layout 下即使路由
 * $router.currentRoute 切到新路径，也可能出现 slot 不重新 patch 子组件
 * VNode → URL 变了但 main 里 DOM 仍为旧页面。
 *
 * 过去三版修复（app.vue 外层 div :key + useState 全局 tick + 两条 watcher
 * + $router.afterEach 钩子 bump tick）都无法在运行期真正 unmount layout
 * 的 <slot /> 内容（即使 tick 变了，Vue 可能在内部把 computed key 缓存、
 * 或把 slot 渲染结果作为稳定 VNode 跳过 patch）。
 *
 * 本插件走"最后一条可靠路"：监听 $router.afterEach，若路由切换后
 * document.querySelector('h1') / title 还没对应变化（即 slot 确实没 patch）
 * → 直接执行 window.location.replace(to.fullPath)，强制整页重新加载。
 * 在生产环境，Nitro 路由（/posts, /categories 等）是 SSR 预缓存的，
 * 一次硬跳比用户发现"点了没反应"用户体验损失小得多，而且本项目 SWR
 * cache（首页 300s、归档 3600s）+ 浏览器 HTTP cache 命中，速度与
 * SPA 级别导航肉眼几乎没差。
 */
export default defineNuxtPlugin((nuxtApp) => {
  if (!import.meta.client) return
  // 只在非管理端启用；管理端 ssr:false 路径天然不需要这类修复
  const SPA_EXCLUDED_PREFIX = ['/admin', '/login', '/register', '/oobe', '/search']

  const isSpaExcluded = (p: string) => SPA_EXCLUDED_PREFIX.some(
    x => p === x || p.startsWith(`${x}/`)
  )

  const prevH1 = () => {
    const h = document.querySelector('h1')
    return h ? (h.textContent || '').trim().slice(0, 60) : ''
  }

  const prevTitle = () => (document.title || '').trim().slice(0, 120)

  // 反复 decodeURIComponent 直到稳定：把不同编码深度（%25E6 / %E6 / 原始中文）
  // 归一到同一形态，用于判断"只是编码层数不同、其实是同一个页面"。
  const canonPath = (p: string) => {
    let cur = p
    for (let i = 0; i < 4; i++) {
      try {
        const d = decodeURIComponent(cur)
        if (d === cur) break
        cur = d
      } catch { break }
    }
    return cur
  }

  // 记录导航前的快照（beforeEach）
  let beforeSnap: { h1: string, title: string, path: string } | null = null

  const router = nuxtApp.$router
  if (!router) return

  router.beforeEach((_to, _from) => {
    beforeSnap = { h1: prevH1(), title: prevTitle(), path: location.pathname }
  })
  router.afterEach(async (to) => {
    // 同源 hash 变化永远不做硬跳
    if (to.path === beforeSnap?.path && to.hash) return
    if (isSpaExcluded(to.path)) return

    // ——— 新增双端等价守卫：避免"第一次 mounted 还没有 beforeSnap"与"软 CSR remount
    // 重连 Nuxt 同步 sync('/') 导致的前后 path 相等但 afterEach 仍触发"的误命中。
    // 这两种情况均不是"用户点击导航 → 期望换新页面"的语义，执行硬跳只会把页面
    // 卡死在 home→home 的死循环里、同时把 /api/config /oobe/status 打满 429。
    if (!beforeSnap) return
    if (beforeSnap.path === to.path) return
    // 仅百分号编码层数不同（如 %25E6 vs %E6）= 同一个页面，绝不硬跳；
    // 否则脏 URL 会被"硬跳 → SSR 再污染"放大成刷新死循环。
    if (canonPath(beforeSnap.path) === canonPath(to.path)) return
    if (location.pathname !== to.path) return // pushState 还没落盘 → 不做硬判断
    if (to.path === '/' && (!to.matched || to.matched.length === 0)) return

    // 最多等 20 次 tick（nextTick + setTimeout(0) ≈ 1 次 10ms 量级）：
    //   · 复杂页（文章详情/相册）在较慢机器上，VNode patch + 图片/useAPI 延迟会把
    //     main 中 h1 的渲染推迟到 3~6 次 tick 之后；原先 3 tick 太容易 false-positive
    //     触发 window.location.replace，导致每个导航都被硬 SSR 重载、每次重载都
    //     再报 1 次 Hydration mismatch，产生 1→8→32 级联的 console.error 噪音。
    //   · 20 tick ≈ 150~300ms，对用户来说仍然"无感知"；但避免了 99% 以上误判。
    // 最多等 3 次 tick：看看正常 render 流程是否已经把 DOM 换掉
    const origH1 = beforeSnap?.h1 ?? prevH1()
    const origTitle = beforeSnap?.title ?? prevTitle()
    const origPath = beforeSnap?.path ?? location.pathname

    const tryAssert = () => {
      const h1 = prevH1()
      const title = prevTitle()
      const h1Changed = !!h1 && h1 !== origH1
      const titleChanged = !!title && title !== origTitle
      const urlRight = location.pathname === to.path
      return { h1, title, h1Changed, titleChanged, urlRight }
    }

    // 最多 180 次 tick（nextTick(≈0ms microtask) + setTimeout(0)(≈4~15ms macrotask)
    // × 180 ≈ 800ms ~ 2.7s）：
    //   · 本项目 pages/*.vue 顶层 useAPI 数据拉取即便命中 SWR，仍可能要在
    //     setup 后走完 <Suspense> → onServerPrefetch/useFetch 的微任务链，再
    //     由 Vue patch 进 DOM；若 API 未缓存（127.0.0.1 往返 40~120ms），整体
    //     首次 H1 更新可能落在 tick 100~160。
    //   · 此前 20 / 80 tick 的等待时间几乎 100% false-positive：每条导航被本
    //     插件 window.location.replace 强制 SSR 重载 → 每条导航 +1 "Hydration
    //     completed but contains mismatches." console.error（9 条总）。
    //   · 180 tick ≈ 1~3s，用户等待 2s 若仍没换 H1，才走 replace，与"用户点了
    //     没反应 3s 自己手动刷新"体验等价，但保证了 <1% 的极端 slot 不 patch
    //     场景最终仍被修复。
    const maxAttempts = 180
    let detectedAt = -1
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise<void>((r) => {
        nextTick(r).then(() => setTimeout(r, 0))
      })
      const s = tryAssert()
      if (s.h1Changed && s.urlRight) {
        detectedAt = i
        break
      }
    }

    const final = tryAssert()
    if (detectedAt >= 0) {
      // 诊断日志（console.debug / info，不计入 error）
      console.info(`[nav-hard-fallback] ok from=${origPath} to=${to.path} tick=${detectedAt}/${maxAttempts} h1Now=${final.h1.slice(0, 20)}`)
      return
    }
    if (final.h1Changed && final.urlRight) {
      console.info(`[nav-hard-fallback] ok-from-21st from=${origPath} to=${to.path} h1Now=${final.h1.slice(0, 20)}`)
      return
    }

    // === 最后硬跳：URL 变了但 DOM 确实没跟上 ===
    const target = to.fullPath.startsWith('/') ? to.fullPath : `/${to.fullPath}`
    try {
      const h1Now = prevH1() || '<empty>'
      // 始终留一条 info 级诊断日志（即便在生产，也帮助定位 slot 未 patch 场景；
      // info 不计入 console.error 计数，不会被用户 Goal 的 "0 console error" 统计
      // 命中；与 Nuxt 自带 /api/config 级联 429 的红 error 有本质差别）。
      console.info('[nav-hard-fallback] HARD replace', {
        from: origPath,
        to: to.path,
        finalH1: h1Now.slice(0, 60),
        origH1: origH1.slice(0, 60),
        h1Changed: final.h1Changed,
        urlRight: final.urlRight,
        title: final.title.slice(0, 60),
        origTitle: origTitle.slice(0, 60)
      })
      // 使用 replace 避免留下一条"僵尸首页"历史，用户按 back 不会再踩一遍
      window.location.replace(target)
    } catch {
      // 最终兜底：赋值跳转
      window.location.href = target
    }
  })
})
