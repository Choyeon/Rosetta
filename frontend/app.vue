<!--
  全局根组件：TooltipProvider 单例 + NuxtLayout/NuxtPage + 客户端浮层（Toaster/主题涟漪）。
  硬契约：<NuxtPage page-key="fullPath"> 保证导航只重建页组件、布局保持挂载，禁止给
  NuxtLayout 外层再加 :key 屏障或在导航钩子里 window.location.replace（历史插件已删除，
  那等于把 SPA 导航降级成整文档重载）；水合级联的软重挂 (__safetyRootKey) 是每文档上限
  2 次的有界恢复，重挂前必先 console.error 留痕，真实修复在构建/服务端层。
-->
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

// 路由进度条颜色用 hsl(var(--primary))：--primary 在 :root/.dark/调色板里重定义，
// 进度条内联 style 作为 body 后代解析该变量，明暗与换肤均自动跟随，无需 JS 分支。
const indicatorColor = 'hsl(var(--primary))'

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

// ====== Hydration 级联防御：根组件软重挂 key ======
// app.vue onErrorCaptured 与 plugins/02-hydration-safety 共享此 useState key，
// 统一硬上限 MAX_SOFT_REMOUNTS 次/文档。重挂前必先 console.error 上报 ——
// 软重挂是"有界恢复"，不是掩盖。真实根因修复在构建/服务端层
// （nuxt.config vite lucide-ssr-fix / setref-nullsafe、nitro spa-serverrendered-zero）。
const __safetyRootKey = useState<number>('__hydration_safety_root_key__', () => 0)
const MAX_SOFT_REMOUNTS = 2

// ====== 页面级 remount 键：仅换页组件，不换布局 ======
// 同组件不同参数的路由（/posts/a → /posts/b、/categories/x → /categories/y、
// 独立页 pages/[slug]）Vue Router 会复用实例，页面 setup 里按 route.params
// 构造的 useAPI key 不重跑 → 用户看到"URL 变了内容没变"。
// NuxtPage 的 page-key 让**页组件**按 fullPath 重建，<NuxtLayout>（顶栏/页脚/
// 侧栏）保持挂载——这是真正的 SPA 导航，不重载文档、不重取布局数据。
// 历史注：曾用 app 级 `:key=__navSlotBusterKey`（plugins/03）把 layout+page 整体
// unmount，再用 plugins/04 的 window.location.replace 兜底；那两条把每次点导航
// 变成整页重载（用户侧"闪一下默认样式再重新加载"），已删除，勿再加回。

const authStore = useAuthStore()
const toast = useToast()

/**
 * 判断是不是 Hydration 级联错误（SSR mismatch → 拆 DOM → instance detach →
 * instance.refs === null → TypeError reading refs）。
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
    if (import.meta.client && __safetyRootKey.value < MAX_SOFT_REMOUNTS) {
      // WHY：先上报再重挂 —— 恢复动作必须留痕，不得静默。
      console.error(`[app] hydration cascade → soft CSR remount ${__safetyRootKey.value + 1}/${MAX_SOFT_REMOUNTS}`, err)
      __safetyRootKey.value++
      return true
    }
    // 预算耗尽（或 SSR 端）：不再掩盖，继续向 Nuxt 默认链传播（vue:error 钩子会再报一次并放弃恢复）。
    return false
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
  // 幂等守卫：useSeo 产出的 title 已自带 " · 站点名" 后缀，直接再拼会产生
  // "标题 · 站点名 · 站点名" 双后缀（SSR curl 实测复现），已含后缀则原样返回。
  titleTemplate: (titleChunk?: string | null) => {
    const name = defaultTitles.value.name || 'Rosetta Blog'
    const sub = defaultTitles.value.sub || ''
    if (titleChunk && String(titleChunk).trim()) {
      const t = String(titleChunk).trim()
      if (t === name || t.endsWith(`· ${name}`)) return t
      return `${t} · ${name}`
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

      <!-- 路由切换进度条：SSR 直出页/慢导航期间给出可见反馈，颜色随主题 --primary 自适应。
           单次渲染于分支之外，覆盖前台与后台全部导航。 -->
      <NuxtLoadingIndicator
        :color="indicatorColor"
        :height="3"
        :throttle="150"
        :duration="8000"
      />

      <!-- ===== SSR / SPA 混合渲染分路 =====
         公开内容页（/、/posts/**、/categories/**、/tags/**、/series/**、/archive、/about、
         /friends、/gallery、/activity、/guestbook、/page/**、/[slug] 独立页）直接
         渲染 <NuxtLayout> + <NuxtPage>，让 SSR 真实内容 HTML 输出（SEO + 首屏直出）。

         后台 / 登录 / 注册 / OOBE / 文档工具 / 搜索 等 ssr:false 精准反选路径：
         依然保留 <ClientOnly> 隔离层，因为 Nitro routeRules 已把这些路由的 SSR 关闭，
         ClientOnly 的 fallback spinner 与 SPA 基线行为一致，消除 layout:false /
         重定向场景首帧 DOM 结构错位导致的 Hydration mismatch。 -->
      <template v-if="needsSpaIsolation">
        <!-- ssr:false 精准反选路径（登录/注册/搜索/管理端）：
             Nitro 层已保证空壳响应不带 hydrate 分支（server/plugins/spa-serverrendered-zero），
             这里保留 ClientOnly 仅用于隔离 layout:false / 重定向场景的首帧结构错位。
             水合级联错误由 app.vue onErrorCaptured + 02-hydration-safety 做有界软重挂（上限 2 次）。 -->
        <NuxtLayout>
          <NuxtPage page-key="fullPath" />
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
        <!-- page-key="fullPath"：换页只重建页组件，<NuxtLayout>（顶栏/页脚）保持挂载，
             同时修掉同组件不同参数路由复用实例导致的"URL 变了内容不变"。
             禁止再加 app 级 :key 屏障或 afterEach window.location.replace 硬跳——
             那会把普通导航降级成整文档重载。 -->
        <NuxtLayout>
          <NuxtPage page-key="fullPath" />
        </NuxtLayout>

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
