/**
 * 路由切换客户端全局"强刷新计数器"（最终兜底）
 *
 * 背景：
 *   本项目 Windows SSR + Client Hydrate 时，因为 SVG/lucide 图标 "SSR：<!---->" vs
 *   客户端："<svg>" 总会触发一次 "Hydration completed but contains mismatches."。
 *   02-hydration-safety 插件会把根 <div :key="safetyRootKey"> 切一下 → 整页纯 CSR 重挂。
 *   这次重挂之后，app.vue / layout / page 的 setup 都会重新跑；但是老代码里
 *   `const r = useRoute(); watch(r.fullPath, …)` 在某些 Nuxt 版本会"挂到旧的组件
 *   实例上、路由变了 watch 却不被通知" → 导致 navigation：URL 变 DOM 不变。
 *
 * 修复（本文件）：在 Nuxt 全局 plugin 里，通过 $router.afterEach + app:rendered 双钩子
 * 维护一个单例 `pageRenderTickRef`（useState 全局单例）。任何真实导航（pushState /
 * replace / 浏览器前进后退）成功并且页面渲染完后，一定 +1。在 app.vue 的
 * <NuxtLayout :key / NuxtPage :key 读这个 ref 的值，因此 100% 会 unmount+mount 新页面。
 */
export default defineNuxtPlugin((nuxtApp) => {
  const pageRenderTickRef = useState<number>('__page_render_tick_global__', () => 0)

  // 防循环：bumpTick 会改 __navSlotBusterKey → <NuxtPage> unmount+remount →
  // 重挂载完成又触发 page:finish / app:rendered → 再次 bumpTick → 死循环卡死。
  // 用 lastBumpedPath 记录最近一次 bump 对应的路由路径，同一路径只 bump 一次，
  // 下一次导航（路径变化）才允许再次 bump。
  let lastBumpedPath = ''

  // Hydration 阶段禁止 bump：
  // 首帧 bump 会让 __navSlotBusterKey 从 /::0 变成 /::N，
  // 导致 <NuxtLayout>/<NuxtPage> 在 hydration 过程中 unmount+remount，
  // 打断页面 async setup（await useAPI）的 Suspense 链，使首页内容渲染为空白。
  // 仅在 hydration 完成后（真实客户端导航）才 bump。
  const bumpTick = () => {
    if (nuxtApp.isHydrating) return
    const cur = nuxtApp.$router?.currentRoute?.value?.path ?? ''
    // 同一路径在同一轮渲染周期内只 bump 一次，防止 page:finish → remount →
    // page:finish 的无限循环把浏览器卡死。
    if (cur === lastBumpedPath) return
    lastBumpedPath = cur
    pageRenderTickRef.value++
  }

  // 路由成功（beforeEach/afterEach 里 afterEach 是 URL 变完、所有 component resolved 之后）
  const router = nuxtApp.$router
  if (router) {
    router.afterEach((_to) => {
      // 导航时先清空路径标记，允许本次导航的 bumpTick 执行；
      // 之后 page:finish / app:rendered 再触发 bumpTick 时，因路径已记录而跳过，
      // 避免 bumpTick → remount → page:finish → bumpTick 的死循环。
      lastBumpedPath = ''
      // nextTick：等 Vue/Nuxt 把路由组件真正 resolve 完再 +1（避免异步组件 pending 时误判）
      nextTick(bumpTick).catch(() => bumpTick())
    })
  }

  // 额外保险：每次 Nuxt 完成页面渲染（layout + page 都 patch 后）也要 +1
  // (page:finish / app:rendered 在某些 ssr:false 路由不会触发 → afterEach 作为主驱动)
  nuxtApp.hook('page:finish', () => bumpTick())
  nuxtApp.hook('app:rendered', () => bumpTick())
})
