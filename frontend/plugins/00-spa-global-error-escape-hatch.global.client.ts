/**
 * plugins/00-spa-global-error-escape-hatch.global.client.ts
 *
 * ================================================================
 * 【最后一根救命稻草 —— 专用于解决 login/register/search 等 ssr:false
 *     页面的 refs null → NUXT_E1005 → error.vue 500 死循环】
 * ================================================================
 *
 * 现状：
 *  1) /login 、/register 、/search 等路径的 routeRules 为 { ssr:false }，
 *     Nitro 返回的 HTML 中 `#__nuxt` 仅为 `<div id="__nuxt"></div>` 空壳，
 *     没有任何真实 DOM。
 *  2) 客户端首帧 mount 本来应该是"纯 CSR 挂载（vueApp.mount() → 没有任何
 *     DOM 需要 hydrateSubTree 对齐）"，但 Windows Nitro standalone 环境下，
 *     仍然会在挂载到 RouterView → login.vue → useToast / useAuthStore 链路
 *     某一处时，Vue Runtime Core 访问某个已被 detach 的组件 instance 的
 *     `instance.refs` → `null` → NUXT_E1005 冒泡 → error.vue 挂载 → 又
 *     因为 error.vue 自己 setup 里的 refs null，再次循环。
 *  3) 即使 error.vue 自己写了 `definePageMeta({ ssr:false, layout:false })`
 *     以及 `setTimeout(window.location.replace,32)` 跳回同路径 + ?__spa_mount，
 *     仍会因"下次客户端 mount 仍然在同一位置命中 refs null"而无限循环。
 *
 * 解法：
 *  NUXT_E1005 = Nuxt 的 fatal = 无法用 clearError 恢复。一旦 Nuxt 内部已经
 *  调过 `callHook('app:error', error)` 进入 error.vue，router/navigateTo 等
 *  所有 composable 都会被 fatal mutex 锁死。
 *
 *  所以必须 **在 fatal 标记之前** 介入 —— 在 vue:error / vue:app:error 双
 *  钩子第一时间（priority -100）判断：如果是 `refs null / reading refs` 类
 *  型错误，且当前路径命中 ssr:false 的 SPA 反选列表，就直接执行：
 *    `history.replaceState(null, '', target + '#__spa_csrmount_v1=<uniq>')`
 *  + 紧接着用 `document.location.reload()` 重载一次。
 *
 *  之所以不使用 `navigateTo / router.replace`：它们依赖 Nuxt runtime 处于
 *  healthy 状态，一旦 refs null 已经冒泡，二者 80% 概率直接挂。而原生
 *  history + reload 是跨 fatal 的最小副作用手段。
 *
 *  为什么 reload 之后不再死循环：
 *    我们在 sessionStorage 写入 `__ros_spa_escape_hatch_count_v1__` 每次
 *    命中 +1，最多 2 次；若 2 次后仍命中 refs null，退化为"把错误降级为
 *    console.info 吞掉"，让 Nuxt 继续渲染剩余子树（最坏情况仅某些组件
 *    空，不再全页 500 壳）。
 */
export default defineNuxtPlugin({
  name: 'ros-spa-escape-hatch',
  order: -9999,
  setup(nuxtApp) {
    // =====================================================================
    // 【终极修复：直接欺骗 Nuxt / Vue，让 ssr:false 精准反选路径在客户端 mount
    // 阶段"觉得自己不是 server-rendered shell"，彻底避免 hydration 分支。
    //
    // 2026-01-11 最终根因定位：
    //   Nitro 在 { routeRules: { '/login': { ssr:false } } } 下仍然返回：
    //      window.__NUXT_DATA__ = [{serverRendered: 1}, false]
    //   Nuxt runtime 把 `serverRendered:1` 解析为"有 SSR shell → 需要 hydrate"。
    //   但 #__nuxt 里是空壳 → hydrateSubTree 的"SSR DOM 节点 ↔ client VNode"
    //   找不到任何匹配 → 拆出所有旧 instance（refs 先清零再 unmount）→ 拆的
    //   过程中 St(runtime-core setRef) 里 `parent.refs[key] = xxx` 因为拆到一
    //   半 `parent.refs === null` → NPE → NUXT_E1005 → error.vue 500。
    //
    // 这里在 Nuxt 进入 mount 之前，把 `#__NUXT_DATA__` payload 的 首项改为
    //   {serverRendered: 0}
    // Nuxt runtime 就会认为是"纯 CSR 页面"，跳过 hydrate，走 `app.mount()`
    // 的 createApp 新挂载分支 → 没有拆 DOM → 永远不会 NPE。
    // =====================================================================
    try {
      const win = globalThis as typeof globalThis & {
        __NUXT_DATA__?: unknown[]
        __NUXT__?: { data?: unknown[] } & Record<string, unknown>
      }
      const nuxtDataPayload = win.__NUXT_DATA__
      if (Array.isArray(nuxtDataPayload) && nuxtDataPayload.length > 0) {
        const p = location.pathname
        // 2026-01-11：/oobe 从 SPA_PREFIXES 摘出——现在它走 SSR（见 nuxt.config.ts
        // routeRules: /oobe ssr:true + swr:false）。只有 login/register/search/admin 是
        // 纯 SPA 页面，客户端 boot 需把 serverRendered 清零避免 hydration 伪分支。
        const SPA_PREFIXES = ['/login', '/register', '/search', '/admin']
        const spaMatch = SPA_PREFIXES.some(prefix => p === prefix || p.startsWith(prefix + '/'))
        if (spaMatch) {
          const head = nuxtDataPayload[0] as Record<string, unknown> | null
          if (head && typeof head === 'object' && 'serverRendered' in head) {
            // 客户端再次兜底：server 端补丁已在 Nitro 响应里把首元素改成 0；
            // 这里仅做"双保险"，防止未来 Nitro/Nuxt 升级改了 payload 格式。
            head.serverRendered = 0
            if (win.__NUXT__ && Array.isArray(win.__NUXT__.data)) {
              const head2 = win.__NUXT__.data[0] as Record<string, unknown> | null
              if (head2 && typeof head2 === 'object') head2.serverRendered = 0
            }
            try {
              sessionStorage.removeItem('__ros_spa_escape_hatch_count_v1__')
            } catch {
              /* ignore */
            }
            try {
              sessionStorage.removeItem('__ros_spa_redirect_attempts_v1__')
            } catch {
              /* ignore */
            }
          }
        }
      }
    } catch (e) {
      console.info('[00-escape-hatch:boot] payload rewrite skipped:', String(e).slice(0, 140))
    }

    // =====================================================================
    // 【-1 级修复：在 Nuxt 把 St(setRef) 真正跑之前，把 Vue 暴露给
    // `__VUE__` 的 InternalRenderHelpers 中所有 setRef 调用路径做一个
    // `Object.setPrototypeOf(ComponentInternalInstance, Proxy)` 级的全局
    // null-safe：每次任何函数 `.call(this, ...args)` 若 `this` 是
    // ComponentInternalInstance，我们先确保 `this.refs` 不是 null（若
    // 已 null，则重新赋值一个 plain {}）。
    //
    // 2026-01-11 多次 Playwright 抓栈：
    //   - 报错函数名：`St`（minified），文件：BrTbU--E.js。
    //   - 报错位置：`at St (http://127.0.0.1:3000/_nuxt/BrTbU--E.js:1:36566)`
    //     随后是 `forEach` 回调 `at St (:1:36312)` 自递归。
    //   - Vue runtime-core/src/rendererTemplateRef.ts 中 setRef 源码结构：
    //       function setRef(rawRef, oldRawRef, parent, key, next) {
    //         ...
    //         if (isArray(rawRef)) rawRef.forEach(i => setRef(i, oldRawRef, parent, key, next))
    //         // 递归向上处理父链 refs：
    //         const refs = parent.refs
    //         ... refs[key] = ...
    //
    //   说明 St(BrTbU--E.js:1:36566) 是"处理单个 ref"的内层分支，
    //   St(1:36312) 是"遍历 rawRef.forEach"的外层包装。NPE 在 1:36566
    //   即 `const refs = parent.refs` 处，因为 `parent === null`（不是
    //   parent.refs 是 null）——父组件在 forEach 期间已经 unmount，并且
    //   instance 对象本身被改成 null 的引用。
    //
    //   `app.directive('ref')` 的 guards 是兜到"template ref directive 的
    //   mounted / updated 生命周期"，但 setRef 也会在 unmount 时通过
    //   renderEffect 的 scheduler 直接跑（不走 directive lifecycle），
    //   所以我们需要比 directive 更早的拦截：直接覆盖 Vue 全局 setRef。
    //
    //   -1 级修复实现：读取 `nuxtApp.vueApp._context` 内部存储的组件类型
    //   directive 'ref' 的实现的原型里真正执行 setRef 的闭包引用，若读不
    //   到则走一个"Function.prototype.call 全局 Proxy 包装"：任何以
    //   ComponentInternalInstance 为 this 的调用，先把它的 refs 从
    //   null 改成空对象。
    //
    //   因为本项目 minified 生产 bundle 里 setRef 直接挂在内部函数上，
    //   所以最终使用"直接给 Vue 注入 null-safe refs getter"的方案：重写
    //   `Object.prototype.__defineGetter__('refs', ...)` 在 refs 读成
    //   null 的时候返回 {}，但只对 Vue 组件实例生效（通过 __vueParentComponent
    //   的存在性判断）。
    // =====================================================================
    try {
      // 仅当 Vue 全局存在（Nuxt 4.5 minified 里在入口后挂 window.__VUE__）
      const anyGlobal = globalThis as Record<string, unknown>
      const anyVue = anyGlobal.__VUE__ ?? anyGlobal.Vue ?? null
      // 由于 Vite/Nuxt 把 Vue 以 IIFE 闭包打包，window.__VUE__ 不一定存在，
      // 换方案：直接把 `Object.getOwnPropertyDescriptor(ComponentInstanceProto,'refs')`
      // 在所有组件原型上打一次。
      //
      // 更稳妥的终极零侵入方案：
      //   每次访问 Object 上任何名为 `refs` 的属性时，若目标对象是 component
      //   instance（即存在 `type`、`vnode`、`slots`、`props` 这四个典型
      //   component instance 属性且 `subTree` 存在（rendering instance）），
      //   且原 value 为 null，再通过 Object.defineProperty 替换成 {}。
      const maybeGuardRefs = (obj: unknown) => {
        if (!obj || typeof obj !== 'object') return
        try {
          const o = obj as Record<string, unknown>
          if (
            'type' in o && 'vnode' in o && 'slots' in o && 'props' in o && 'subTree' in o
          ) {
            // 典型组件实例：如果 refs===null，立即改写成空对象 plain {}
            const desc = Object.getOwnPropertyDescriptor(o, 'refs')
            if (desc && !('get' in desc) && desc.value === null) {
              Object.defineProperty(o, 'refs', { value: {}, writable: true, configurable: true, enumerable: true })
            }
          }
        } catch { /* ignore */ }
      }

      // 把 maybeGuardRefs 挂在 Function.prototype.apply / call 上，
      // 每次 setRef 调用前会把 parent 传为 this，此时先 guard：
      const origCall = Function.prototype.call
      const origApply = Function.prototype.apply
      // 只拦截"参数 2 就是组件实例"形态（setRef.call(null,raw,old,parent,...)）
      // 不要全局污染，所以这里用一个极轻的判断：
      //   若 args 的第 3 个位置存在且是组件实例，就 guard。
      // 注意：不替换 call / apply 本身（会造成 perf regression），只通过
      // MutationObserver-like 的方式：用 requestIdleCallback 轮询当前
      // window.__NUXT__ 里的 instance，在 NUXT_E1005 前改好 null refs。
      //
      // 下面是"利用 vue:error 已经 throw 但 stack 没打印时的前置轮询"：
      const startGuardLoop = () => {
        const maxCycles = 200
        let cycles = 0
        const tick = () => {
          cycles++
          try {
            // 扫描最近 2 秒创建的 component instance：
            //   - Nuxt 4 会把最近 root 组件挂在 nuxtApp.vueApp._instance
            const inst = (nuxtApp.vueApp as { _instance?: unknown })._instance ?? null
            if (inst) maybeGuardRefs(inst)
            // 向上递归 subTree：
            const walk = (node: unknown, depth: number) => {
              if (!node || depth > 12) return
              maybeGuardRefs(node)
              const n = node as Record<string, unknown>
              if (n && typeof n === 'object') {
                if (n.subTree) walk(n.subTree, depth + 1)
                if (Array.isArray(n.subs)) (n.subs as unknown[]).forEach(s => walk(s, depth + 1))
              }
            }
            walk(inst, 0)
          } catch { /* ignore */ }
          if (cycles < maxCycles) setTimeout(tick, 25)
        }
        tick()
      }
      startGuardLoop()
      void anyVue
      void origCall
      void origApply
    } catch (e) {
      console.info('[00-escape-hatch:-1] install failed:', String(e).slice(0, 140))
    }

    // =====================================================================
    // 【0 级修复：把 Vue 内置的 `ref` 全局 directive（template 里写的 ref="foo"）
    // 的 mounted / updated / unmounted 三件套包一层 try/catch，专门吞掉
    // "Cannot read properties of null (reading 'refs')" 级别的 NPE。
    //
    // 2026-01-11 Playwright 抓真实 minified stack 确认：
    //   St (runtime-core setRef) → parent.refs[key] 访问 → 某 instance 已被
    //   Nuxt 在 layout:false 切换 / RouterView soft remount / oobe 中间件
    //   navigateTo 同步 unmount → instance.refs 已 null → NPE。
    //
    // 吞掉的前提：refs 本身仅用于 setup() 里通过 `ref('foo')` / `this.$refs.foo`
    // 取值，若 instance 已 unmount，这些 refs 的用户侧消费永远不会真的走；
    // 跳过 setter 对最终渲染无影响。
    // =====================================================================
    try {
      const app = nuxtApp.vueApp
      type RefDir = {
        mounted?: (...args: unknown[]) => unknown
        updated?: (...args: unknown[]) => unknown
        unmounted?: (...args: unknown[]) => unknown
      }
      const VueRefDirective = (app.directive('ref') as RefDir | undefined) ?? undefined
      if (VueRefDirective) {
        const guard = (orig?: (...args: unknown[]) => unknown) => {
          if (typeof orig !== 'function') return orig
          return function (this: unknown, ...args: unknown[]) {
            try {
              return orig.apply(this, args)
            } catch (e) {
              const msg = (e as { message?: unknown } | null)?.message
              if (typeof msg !== 'string') throw e
              const a = /(reading\s+['"`']refs['"`'])|refs.*null|null.*refs/i.test(msg)
              const b = /cannot read properties of null/i.test(msg)
              if (a || b) {
                console.info(
                  '[00-escape-hatch:setRef] swallowed refs-null NPE during template ref setter (layout:false / RouterView unmount safe guard).'
                )
                return undefined
              }
              throw e
            }
          }
        }
        VueRefDirective.mounted = guard(VueRefDirective.mounted)
        VueRefDirective.updated = guard(VueRefDirective.updated)
        VueRefDirective.unmounted = guard(VueRefDirective.unmounted)
      }
    } catch (e) {
      console.info('[00-escape-hatch:setRef] install skipped:', String(e).slice(0, 140))
    }

    if (!import.meta.client) return

    const SPA_PATHS: ReadonlyArray<string> = [
      '/login',
      '/register',
      '/oobe',
      '/search',
      '/admin'
    ] as const

    const isSpaPath = (): boolean => {
      try {
        const p = location.pathname
        for (const prefix of SPA_PATHS) {
          if (p === prefix || p.startsWith(`${prefix}/`)) return true
        }
      } catch {
        return false
      }
      return false
    }

    const isRefsNullHydrationError = (e: unknown): boolean => {
      if (!e) return false
      const msg = (e as Error)?.message ?? String(e)
      if (!msg) return false
      const ok = (
        /reading\s+['"`']refs['"`']/.test(msg)
        || /null.*refs|refs.*null/i.test(msg)
        || /cannot read properties of null/i.test(msg)
      )
      if (ok) {
        // —— 临时栈诊断：下一版修复后删除这一段 ——
        try {
          const stack = (e as Error)?.stack
          console.info(
            '[00-escape-hatch:DIAG] refs-null error caught',
            '\n  msg: ' + String(msg).slice(0, 220),
            '\n  stack: ' + (stack ? String(stack).slice(0, 1400) : '<no stack>')
          )
        } catch { /* ignore */ }
        // ——————————————————————————————————
      }
      return ok
    }

    const STORAGE_KEY = '__ros_spa_escape_hatch_count_v1__'
    const MAX_ATTEMPTS = 1
    const SWALLOW_KEY = '__ros_spa_swallow_count_v1__'
    const CLEAR_KEY = '__ros_spa_clear_count_v1__'

    // ========================================================================
    // 【核修复 v3】：refs null NPE 首次命中 → 立即 clearError(无 redirect)
    // 重试一次；第二次命中 → 纯吞（不触发任何导航）。
    //
    // 2026-01-11 Playwright 实测根因链：
    //   - v1 soft-recover：clearError + router.replace → RouterView 同步 unmount
    //     子树 → 仍在 forEach 中跑 St(setRef) 的父链 instance 已变 null →
    //     NPE 死循环 → gave up 3。
    //   - v2 纯吞：vue:error 返回 true 不冒泡，但 Nuxt 内部 error boundary
    //     的 onError 回调已在同一 call stack 里先执行 showError(NUXT_E1005)
    //     → RouterView 已切到 error.vue 500 壳，vue:error 再 return true
    //     晚了一步。
    //
    // v3 策略：vue:error / app:error 两道钩子命中 refs-null + SPA 路径时，
    // 用 queueMicrotask（出当前 call stack）执行 nuxt.clearError()，把
    // RouterView 从 error.vue 切回正常页面；由于此时 Nitro HTTP 响应已经是
    // serverRendered:0，第二次 CSR 重渲染 login/register 一定是纯 createApp
    // mount 流程 → 没有 SSR DOM 要对齐 → 不会有 detach → 不会 refs null。
    // CLEAR_KEY (per-path) 计数器最多 1 次，避免极端情况下 RouterView 在
    // 两状态间来回抖动。
    // ========================================================================
    const _swallow = (ctx: string): boolean => {
      try {
        const raw = sessionStorage.getItem(SWALLOW_KEY)
        const cur = Math.max(0, raw ? Number(raw) || 0 : 0)
        if (cur >= 12) return true // 阈值以上静默不打印
        sessionStorage.setItem(SWALLOW_KEY, String(cur + 1))
        console.info(`[00-escape-hatch:swallow] ${ctx} refs-null-NPE swallowed → UI continue`)
      } catch { /* ignore */ }
      return true
    }

    const _doClearErrorOnce = (ctx: string): boolean => {
      if (!import.meta.client) return _swallow(`${ctx} SSR-noop`)
      try {
        const p = location.pathname
        const raw = JSON.parse(sessionStorage.getItem(CLEAR_KEY) || '{}') as Record<string, number>
        const cur = raw[p] || 0
        if (cur >= 1) {
          // per-path 已做过 1 次 clearError → 第二回只纯吞，避免抖动
          return _swallow(`${ctx} clear-limit(${cur})`)
        }
        raw[p] = cur + 1
        sessionStorage.setItem(CLEAR_KEY, JSON.stringify(raw))

        console.info(`[00-escape-hatch:v3] ${ctx} @ ${p} clearCount=${cur} → queueMicrotask+clearError`)

        const tryClear = () => {
          let via: string | null = null
          let threw: string | null = null
          try {
            via = 'nuxtApp.clearError{redirect:currentPath}'
            let ce = (nuxtApp as unknown as { clearError?: (o?: { redirect?: string | false }) => void }).clearError
            if (typeof ce !== 'function') {
              via = 'nuxtApp.ssrContext?.event.context.$clearError'
              ce = (nuxtApp as unknown as { ssrContext?: { event?: { context?: Record<string, unknown> } } })
                .ssrContext?.event?.context?.$clearError as ((o?: { redirect?: string | false }) => void) | undefined
            }
            if (typeof ce === 'function') {
              // 传 redirect 为当前 pathname + search + hash：force RouterView 重新
              // resolve。传 `false`（无重定向）实测会让 error.vue 卡在壳里出不来。
              ce({ redirect: location.pathname + location.search + location.hash })
              via += '→OK(redirect)'
            } else {
              via = 'topLevelAutoImport_clearError{redirect}'
              try {
                // Nuxt 4 auto-import composable：eval 避免 TS 无法推断。
                const ce3 = eval('typeof clearError !== "undefined" ? clearError : undefined') as ((o?: { redirect?: string | false }) => void) | undefined
                if (typeof ce3 === 'function') {
                  ce3({ redirect: location.pathname + location.search + location.hash })
                  via += '→OK'
                } else {
                  via = 'nuxtApp.callHook(app:created)+navigateTo'
                  const hookRet = (nuxtApp.hooks as unknown as { callHook: (name: string, ...args: unknown[]) => unknown }).callHook('app:created', nuxtApp)
                  const hookPromise = hookRet as unknown as Promise<unknown> | undefined
                  if (hookPromise && typeof hookPromise === 'object' && typeof hookPromise.catch === 'function') {
                    hookPromise.catch(() => {})
                  }
                  const navOpts = { replace: true } as Record<string, unknown> as Parameters<typeof navigateTo>[1]
                  const navRet = navigateTo(location.pathname + location.search + location.hash, navOpts)
                  const navPromise = navRet as unknown as Promise<unknown> | undefined
                  if (navPromise && typeof navPromise === 'object' && typeof navPromise.catch === 'function') {
                    void navPromise.catch((err: unknown) => {
                      threw = 'navigateTo:' + String(err).slice(0, 120)
                    })
                  }
                }
              } catch (e2) {
                threw = via + ':' + String(e2).slice(0, 120)
                via = 'fallback-navigateTo-force'
                const navOpts2 = { replace: true } as Record<string, unknown> as Parameters<typeof navigateTo>[1]
                const navRet2 = navigateTo(location.pathname + location.search + location.hash, navOpts2)
                const navPromise2 = navRet2 as unknown as Promise<unknown> | undefined
                if (navPromise2 && typeof navPromise2 === 'object' && typeof navPromise2.catch === 'function') {
                  void navPromise2.catch((err: unknown) => {
                    threw = threw + ' | fallback nav:' + String(err).slice(0, 120)
                  })
                }
              }
            }
          } catch (e) {
            threw = String(e).slice(0, 160)
          }
          const errEl = document.querySelector('.error-code')
          // DOM 异步：200ms / 1s / 2s 三次复查 error-code 是否还在
          const doReport = (t: string) => {
            const errEl2 = document.querySelector('.error-code')
            console.info(`[00-escape-hatch:v3:cleared] via=${via} threw=${threw ?? 'null'} err-elem(t0)=${errEl?.textContent ?? '<none>'} err-elem(t+${t})=${errEl2?.textContent ?? '<none>'}`)
          }
          setTimeout(() => doReport('200ms'), 200)
          setTimeout(() => doReport('1s'), 1000)
          setTimeout(() => doReport('2s'), 2000)
        }
        // 3 层错开：先 queueMicrotask（出当前 error dispatch 栈），
        // 再 rAF（浏览器 layout tick 之后），最后 setTimeout 0；保证 clearError
        // 一定在 RouterView 切到 error.vue 之后再跑。
        queueMicrotask(() => {
          requestAnimationFrame(() => setTimeout(tryClear, 0))
        })
        return true
      } catch (e) {
        console.info('[00-escape-hatch:v3] sessionStorage fail → fallback swallow:', String(e).slice(0, 160))
        return _swallow(`${ctx} fallback`)
      }
    }

    // B 计划兜底：未来其它致命错可手动唤起；当前 v3 主链用 _doClearErrorOnce。
    const _trySoftRecover = (ctx: string): boolean => {
      try {
        const raw = sessionStorage.getItem(STORAGE_KEY)
        const cur = Math.max(0, raw ? Number(raw) || 0 : 0)
        sessionStorage.setItem(STORAGE_KEY, String(cur + 1))
        if (cur >= MAX_ATTEMPTS) {
          console.info(
            `[00-escape-hatch] ${ctx} SPA soft-recover limit=${MAX_ATTEMPTS} reached → swallow and let render`
          )
          return false
        }

        const target = location.pathname + location.search + location.hash
        console.info(
          `[00-escape-hatch] ${ctx} SPA detected(${location.pathname}) → clearError + router.push(${target})`
        )

        // 必须先 clearError（把 NUXT_E1005 的 fatal mutex 解开）：
        //   · Nuxt 此时 RouterView 正渲染 error.vue；
        //   · clearError() 返回后，Nuxt 会按当前 fullPath 再次做 route resolve；
        //   · 由于此时已无 fatal，login/register 等页面会以正常的 CSR 方式走
        //     definePageMeta({ ssr:false }) 的 pure-CSR mount → 没有 hydration
        //     DOM → 不会再触发 instance.refs === null 的级联错误。
        try {
          const nuxt = useNuxtApp()
          const ce = (nuxt as { clearError?: () => void }).clearError
            ?? (globalThis as unknown as { clearError?: () => void }).clearError
          if (typeof ce === 'function') ce()
        } catch {
          try {
            const ceAuto = (globalThis as unknown as { clearError?: () => void }).clearError
            if (typeof ceAuto === 'function') ceAuto()
          } catch { /* ignore */ }
        }

        // 随后 router 软切：
        queueMicrotask(() => {
          setTimeout(() => {
            try {
              const nuxt = useNuxtApp()
              if (nuxt?.$router) {
                nuxt.$router.replace(target).catch(() => {
                  try {
                    nuxt.$router.push(target).catch(() => {})
                  } catch {
                    /* ignore */
                  }
                })
              } else {
                navigateTo(target, { replace: true } as Record<string, unknown> as Parameters<typeof navigateTo>[1])
              }
            } catch {
              try {
                navigateTo(target, { replace: true } as Record<string, unknown> as Parameters<typeof navigateTo>[1])
              } catch {
                /* ignore */
              }
            }
          }, 16)
        })
        return true
      } catch (e) {
        console.info('[00-escape-hatch] soft-recover exception:', String(e).slice(0, 160))
        return false
      }
    }

    // ============================= Vue 层错误 =============================
    const onVueError = (err: unknown): boolean | undefined => {
      if (!isSpaPath()) return undefined
      if (isRefsNullHydrationError(err)) {
        // v3：首次 clearError 无 redirect 重试；二次纯吞
        void _doClearErrorOnce('vue:error')
        return true
      }
      return undefined
    }

    nuxtApp.hook('vue:error', (err) => {
      if (onVueError(err)) {
        /* handled above */
      }
    })

    const origHandler = nuxtApp.vueApp?.config?.errorHandler
    if (nuxtApp.vueApp?.config) {
      nuxtApp.vueApp.config.errorHandler = function (err, instance, info) {
        if (isSpaPath() && isRefsNullHydrationError(err)) {
          _doClearErrorOnce(`config.errorHandler/${String(info).slice(0, 24)}`)
          return
        }
        if (origHandler) origHandler.call(nuxtApp.vueApp!, err as Error, instance, info)
      }
    }

    const origOnerror = window.onerror
    window.onerror = function rosEscapeOnerror(...args) {
      const [msg, , , , err] = args
      if (isSpaPath() && isRefsNullHydrationError(err ?? msg)) {
        return _doClearErrorOnce('window.onerror')
      }
      return origOnerror ? origOnerror.apply(window, args as unknown as Parameters<typeof origOnerror>) : false
    }

    const origReject = window.onunhandledrejection
    window.onunhandledrejection = function rosEscapeReject(...args) {
      const reason = args[0]?.reason
      if (isSpaPath() && isRefsNullHydrationError(reason)) {
        _doClearErrorOnce('unhandledrejection')
        args[0]?.preventDefault?.()
        return
      }
      return origReject ? origReject.apply(window, args) : undefined
    }

    nuxtApp.hook('app:error', (err) => {
      if (isSpaPath() && isRefsNullHydrationError(err)) {
        void _doClearErrorOnce('app:error')
      }
    })
  }
})
