/**
 * plugins/01-site-bootstrap.global.ts
 *
 * 在任何布局 (layouts/*) 或页面 (pages/*) 的 setup() 运行之前，
 * 以异步 Nuxt Plugin 的方式确保站点设置（useSite.ensureLoaded）与激活主题
 * （useFrontendTheme.ensureLoaded）加载完成。
 *
 * ====== 本文件是 "Hydration node mismatch (rendered on server:DIV / client:Symbol(v-cmt))"
 *        生产级根治措施，替代之前的 pages/index.vue 与 layouts/default.vue 顶层 await 方案。
 *
 * 【根因回顾】
 * Vue <script setup> SFC 编译器：只要源码顶层存在 `await ...` 词法出现，无论分支是否
 * 执行，都会把生成的 setup() 标记为 async 函数。SSR 下 Suspense 正确阻塞等 Promise
 * resolve 再出真实 DOM。但客户端 Hydration 时：
 *
 *   1. setup() 调用后返回 Promise（无论 Promise 多快 resolve，始终是 Promise 对象）。
 *   2. Vue 的 Hydrate Diff 首帧是**同步**阶段。由于 Promise 的 then 回调至少要等
 *      下一个微任务才能执行，Suspense 的同步判定分支（"setup 返回值是否 Promise 已
 *      settled"）必然是 pending。
 *   3. Suspense 渲染 fallback = Comment vnode（Symbol(v-cmt)）作为首帧子节点，
 *      而此时 SSR 已在相同位置渲染了真实的 div 子树。
 *   4. 下一微任务 Promise resolve → Suspense 替换子树为真实内容，触发 DOM diff：
 *      "Hydration node mismatch: server DIV vs client Symbol(v-cmt)" 与
 *      "Hydration completed but contains mismatches"。
 *
 * 【修复手段】
 *   将所有需要异步 await 的 ensureLoaded 行为，从页面 / 布局 setup 顶层移入本插件的
 *   defineNuxtPlugin(async () => { ... }) 钩子。Nuxt 的启动顺序是：
 *       Server plugins → Middleware → Layout setup → Page setup
 *       Client plugins (hydrating) → Layout setup → Page setup
 *   插件的 async Promise 是 NuxtApp 层的阻塞单元，**完全不参与 Vue RouterView
 *   内部 Suspense 的 pending 判定**。因此本插件 resolve 之后：
 *       - useSite.state.value.loaded === true
 *       - useFrontendTheme.state.value.loaded === true
 *   到 layouts / pages setup() 执行时，100% 已同步就绪，setup 无需任何 await，
 *   编译器产出 100% 同步 setup() → Suspense 首帧 div 匹配 SSR 结构 → 零 Hydration。
 *
 * 【与旧方案（middleware/*.global.ts）的差异】
 *   - 旧方案在 middleware 中调用 useSite()/useFrontendTheme()，后者 useFrontendTheme()
 *     内部会立即执行 `const route = useRoute()`（确保可调用可组合函数生命周期正确）。
 *     但 Nuxt 不允许在 middleware 中使用 useRoute()（应改用 defineNuxtRouteMiddleware
 *     的 to/from 参数）→ 抛出 NUXT_E2005，useRoute() 返回错误的路由（/__nuxt_error
 *     或空路径）→ app.vue 的 needsSpaIsolation 误判为 SPA Skeleton → 额外产生 class
 *     不匹配 / children 数量不匹配 Hydration warning（见 /posts 页面的 class
 *     "w-full items-center justify-center" vs "font-sans flex flex-col" bug）。
 *   - 新方案在 Plugin 上下文中，Nuxt 文档支持在插件内调用所有 composables 与 useRoute；
 *     没有 NUXT_E2005 警告，也不会污染路由判定，完全干净。
 *
 * 【开销】
 *   ensureLoaded() 内部有 state.loaded === true 短路（同步 return），因此：
 *   · SSR 首请求：真执行后端 HTTP，写入 useState payload 供客户端 Hydrate。
 *   · 客户端每次 SPA 路由切换：本插件不再重复执行（plugins 仅在 app 创建时执行一次）。
 *   · 后续跳转时页面代码里的 ensureLoaded 冗余 fire-and-forget：0 开销。
 */
export default defineNuxtPlugin(async () => {
  const site = useSite()
  const ft = useFrontendTheme()
  try {
    await site.ensureLoaded()
    await ft.ensureLoaded()
  } catch (err) {
    // Plugin 异常：不能阻塞应用（否则 Nuxt 渲染死循环）。
    // 下游 useSeo/computed 都会对 state=undefined 做安全兜底。
    if (import.meta.dev) {
      console.warn('[plugin:01-site-bootstrap] ensureLoaded failed:', err)
    }
  }
})
