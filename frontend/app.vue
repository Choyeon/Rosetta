<script setup lang="ts">
import { Toaster } from 'vue-sonner'
import { useI18n } from 'vue-i18n'
import { useTheme } from '~/composables/useTheme'
import { useScrollReveal } from '~/composables/useReadingUX'
import { useAuthStore } from '~~/stores/auth'
import { useToast } from '~~/composables/useToast'
import ThemeRippleOverlay from '~~/components/ThemeRippleOverlay.vue'
import { TooltipProvider } from '~~/components/ui/tooltip'

const _route = useRoute()
const { locale, t } = useI18n()
const { isDark: isDarkTheme } = useTheme()
useScrollReveal()

/**
 * 需要走 SPA 隔离（<ClientOnly> 包裹）的路径集合。
 * 与 nuxt.config.ts routeRules 的 ssr:false 精准反选表保持一致：
 *   · /admin/**  · /login  · /register  · /oobe
 *   · /admin/docs/**  · /search/**
 * 这些路径 Nitro 本身 ssr:false，即使 SSR 了 ClientOnly fallback 也不会污染 SEO；
 * ClientOnly 的作用是消除 layout 重定向 / layout:false 首帧 DOM 结构错位。
 *
 * 2026-01-11 补充：/oobe 已改成 SSR（routeRules: swr:false + no-store、不再 ssr:false），
 * 不再命中"裸 NuxtPage"隔离分支；oobe.global SSR 分支在中间件阶段就已经 302 跳
 * 走了（已安装 → /，未安装 → 继续 /oobe），不需要裸隔离。
 */
const SPA_ISOLATION_PREFIXES: ReadonlyArray<string> = [
  '/admin',
  '/login',
  '/register',
  '/search'
]
const needsSpaIsolation = computed(() => {
  const p = _route.path
  for (const prefix of SPA_ISOLATION_PREFIXES) {
    if (p === prefix || p.startsWith(`${prefix}/`)) return true
  }
  return false
})

// ====== Hydration 级联错误防御：根组件 remount key ======
// 由 plugins/02-hydration-safety.global.client 写入此全局 useState key。
// 若 Windows SSR 首帧仍有 defineComponent 图标 → empty comment 残留 mismatch →
// refs 变 null → 这里直接切换根 key → 整页转纯 CSR 重新挂载（不会再 detach → 不再级联）。
const __safetyRootKey = useState<number>('__hydration_safety_root_key__', () => 0)

// ====== 路由切换 → 同 layout 间 slot 不 memoization 的"硬屏障 key" ======
// 由 plugins/03-global-page-render-tick.client.ts 在 $router.afterEach / page:finish
// / app:rendered 三路 bump；`useState('__page_render_tick_global__')` 为 window 级
// 单例，即使 02-hydration-safety 触发整页重挂（safetyRootKey++）、app.vue 实例
// 被销毁重建，下一次 setup 仍然能读到"累计最新 tick 值"，保证新旧 key 严格不等
// → NuxtLayout 内 <NuxtPage>（以及外层的包装 div）必定 unmount + remount →
// H1 / main 里的 DOM 100% 被 patch 成新页面，不再出现 "URL 变了 H1 不变"
// 的用户侧顽疾（之前误判 false-positive 导致 window.location.replace 硬跳每次
// +1 条 Hydration error，被 04 插件的 HARD replace 打满 9 条 console.error）。
//
// 组成形式：<path_without_hash>::<page_render_tick>。
//   · SSR 端：tick 默认 0 → key = path::0，与客户端首帧 hydrate 前相等 → key 字节一致。
//   · 客户端导航：$router.afterEach 先 bump tick → 再触发 page:finish / app:rendered
//     再 bump 两次（2~3 次 bump / 导航 / 每条）→ 每轮导航 key 一定严格变大，
//     即使用户来回点同一个路径，由于 afterEach 每次都会 bump，key 也保证不同
//     → 一定 unmount。
const __pageRenderTick = useState<number>('__page_render_tick_global__', () => 0)
const __navSlotBusterKey = computed(() => `${_route.fullPath.split('#')[0]}::${Number(__pageRenderTick.value || 0)}`)
if (import.meta.client) {
  const w = globalThis as typeof globalThis & {
    __ROS_NAV_KEY_TRACE__?: Array<{ t: number, k: string }>
  }
  w.__ROS_NAV_KEY_TRACE__ = w.__ROS_NAV_KEY_TRACE__ || []
  watch(__navSlotBusterKey, (k) => {
    try {
      w.__ROS_NAV_KEY_TRACE__!.push({ t: Date.now(), k: String(k) })
    } catch {
      // ignore: push may throw when window has been torn down (soft-CSR remount race)
    }
  }, { immediate: true })
}

const authStore = useAuthStore()
const toast = useToast()

/**
 * 判断是不是 Hydration 级联错误（SSR mismatch → 拆 DOM → instance detach →
 * instance.refs === null → TypeError reading refs）。
 *
 * 这类错误不是业务错误，不应该对用户 toast 报错；
 * 交由 02-hydration-safety 切换 __safetyRootKey 做静默 CSR 重挂载。
 */
const isHydrationCascade = (err: unknown): boolean => {
  const s = err instanceof Error ? err.message : String(err)
  if (!s) return false
  const lc = s.toLowerCase()
  if (lc.includes('hydration') || lc.includes('mismatch')) return true
  if (s.includes('reading refs') || (lc.includes('null') && lc.includes('refs'))) return true
  return false
}

onErrorCaptured((err) => {
  if (isHydrationCascade(err)) {
    // 静默 + 触发根重挂
    if (import.meta.client) __safetyRootKey.value++
    return true
  }
  if (import.meta.client) {
    const msg = err instanceof Error ? err.message : String(err)
    // 防止重复提示：由 error-handler.client.ts 插件处理的错误已经会弹 toast
    if (!msg.includes('Must be called at the top of a `setup` function')) {
      toast.error(msg || '发生未知错误')
    }
  }
  // 不阻止错误继续向上传播，保留控制台堆栈
  return false
})

onMounted(() => {
  if (import.meta.client) {
    authStore.initialize()
  }
})

// ====== 全局站点配置：提前加载，保证 titleTemplate 里的站点名是真实数据 ======
const site = useSite()
// 注意：app.vue 没有 await（Nuxt root 组件本身不阻塞）
// 真实站点名由 layouts/default.vue 的 ensureLoaded 与 publicConfig 共同保证；
// 这里 titleTemplate 写成 computed → 依赖变化时会自动更新 HTML title。
const defaultTitles = computed(() => ({
  name: site.siteTitle.value || 'Rosetta Blog',
  sub: site.siteSubtitle.value || ''
}))

useHead(() => ({
  // 页面标题模板：页面 title 如果有，显示 "页面 · 站点名"；否则 "站点名 · 副标题"
  titleTemplate: (titleChunk?: string | null) => {
    const name = defaultTitles.value.name || 'Rosetta Blog'
    const sub = defaultTitles.value.sub || ''
    if (titleChunk && String(titleChunk).trim()) {
      return `${String(titleChunk).trim()} · ${name}`
    }
    if (sub) return `${name} · ${sub}`
    return name
  },
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1' },
    { name: 'theme-color', content: 'hsl(201 96% 52%)' }
  ],
  link: [
    { rel: 'icon', href: '/favicon.ico' },
    { rel: 'apple-touch-icon', href: '/logo/rosetta-primary-icon.png' }
  ],
  htmlAttrs: {
    lang: () => locale.value || 'zh'
  }
}))
</script>

<template>
  <!-- 全局 TooltipProvider：保证无论 layout 是否启用（login/oobe/register = layout:false），
       所有 <Tooltip>/<TooltipTrigger> 都能拿到注入上下文，避免 reka-ui 报错。
       注：layouts/default.vue / admin.vue 中不再嵌套 TooltipProvider，
           由 app.vue 全局单例保证注入上下文唯一且首渲染一致。 -->
  <TooltipProvider :delay-duration="0">
    <div :key="__safetyRootKey">
      <!-- Skip-link：a11y 跳转到主内容；视觉隐藏，仅键盘 focus-visible 时出现。
         href="#main" 需要布局里有 id="main" 的主内容容器：default/admin 都已保证。
         external 避免 Nuxt router 拦截导致锚点在 layout:false 下解析失败。 -->
      <a
        id="skip-link"
        href="#main"
        class="skip-link focus-ring-animated"
      >
        {{ t?.('a11y.skipToMain') ?? 'Skip to main content' }}
      </a>

      <!-- ===== SSR / SPA 混合渲染分路 =====
         公开内容页（/、/posts/**、/categories/**、/tags/**、/series/**、/archive、/about、
         /friends、/gallery、/activity、/guestbook、/page/**、/[slug] 独立页）直接
         渲染 <NuxtLayout> + <NuxtPage>，让 SSR 真实内容 HTML 输出（SEO + 首屏直出）。

         后台 / 登录 / 注册 / OOBE / 文档工具 / 搜索 等 ssr:false 精准反选路径：
         依然保留 <ClientOnly> 隔离层，因为 Nitro routeRules 已把这些路由的 SSR 关闭，
         ClientOnly 的 fallback spinner 与 SPA 基线行为一致，消除 layout:false /
         重定向场景首帧 DOM 结构错位导致的 Hydration mismatch。 -->
      <template v-if="needsSpaIsolation">
        <!-- ssr:false 精准反选路径（登录/注册/OOBE/搜索/管理端）：
             · 2026-01-11 曾移除 NuxtLayout 以避免 refs null 级联错误，
               但这导致 admin 布局（侧边栏/顶栏）无法渲染。
             · 现已由 02-hydration-safety 插件处理 hydration 问题，
               恢复 NuxtLayout 以保证布局正常渲染。 -->
        <NuxtLayout>
          <NuxtPage />
        </NuxtLayout>
        <ClientOnly>
          <Toaster
            position="bottom-right"
            :duration="3600"
            :close-button="true"
            :rich-colors="false"
            :toast-options="{ class: 'backdrop-blur-md' }"
            :theme="isDarkTheme ? 'dark' : 'light'"
          />
          <ThemeRippleOverlay />
          <template #fallback>
            <div aria-hidden="true" />
          </template>
        </ClientOnly>
      </template>

      <template v-else>
        <!-- 外层 div 携带 `:key=__navSlotBusterKey`（由 plugin 03 在路由 afterEach
             / page:finish / app:rendered 三路 bump 的全局 tick）做 unmount 硬屏障：
             每次导航后 key 一定严格不同 → NuxtLayout + NuxtPage 一定 unmount +
             remount → 新页面 async useAPI + Suspense 的微任务链虽然仍要 tick 40~160
             才能完成，但 H1 / main 的 DOM 一定是新页面 patch 进去（非旧页面残留）
             → 04 插件 false-positive window.location.replace 不再触发 → 每条导航
             不再额外 +1 Hydration mismatch console.error。 -->
        <div :key="__navSlotBusterKey">
          <NuxtLayout>
            <NuxtPage />
          </NuxtLayout>
        </div>

        <ClientOnly>
          <div class="client-only-overlays">
            <Toaster
              position="bottom-right"
              :duration="3600"
              :close-button="true"
              :rich-colors="false"
              :toast-options="{ class: 'backdrop-blur-md' }"
              :theme="isDarkTheme ? 'dark' : 'light'"
            />
            <ThemeRippleOverlay />
          </div>
          <template #fallback>
            <div
              class="client-only-overlays"
              aria-hidden="true"
            />
          </template>
        </ClientOnly>
      </template>
    </div>
  </TooltipProvider>
</template>
