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
const { locale } = useI18n()
useTheme()
useScrollReveal()

const authStore = useAuthStore()
const toast = useToast()

onErrorCaptured((err) => {
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
    <!-- === SPA + ssr:false 模式下彻底消除 Hydration mismatch 的终极隔离 ===
         Nitro 为所有路由生成通用的 index.html fallback 骨架（基于 / 路由的 default layout），
         但首次访问可能被 middleware 重定向到其他 layout 的页面（如 /login 的 layout:false、
         /admin 的 layout:admin），导致 Nitro 骨架 DOM 与 Vue 首渲染 VNode 结构错位。
         ClientOnly 让首渲染输出与 Nitro 骨架无关的确定性 fallback（loading 占位符），
         Hydrate 完成后再切换到真实 <NuxtLayout>，两者完全解耦，从根源消除 mismatch。
         SSR 收益在当前阶段（渐进式 SSR：全 SPA 基线）为零，此隔离无副作用。 -->
    <ClientOnly>
      <NuxtLayout>
        <!-- 页面过渡由 nuxt.config 的 app.pageTransition 驱动（Nuxt 原生机制）。
             不要在此手动包裹 <Transition> / <Suspense>：旧结构在链式重定向时
             out-in 过渡与异步页面组件相互等待，导致渲染管线静默死锁（页面空白）。 -->
        <NuxtPage />
      </NuxtLayout>

      <Toaster
        position="bottom-right"
        :duration="3600"
        :close-button="true"
        :rich-colors="false"
        :toast-options="{ class: 'backdrop-blur-md' }"
        theme="light"
      />

      <!-- 全局单例：圆形扩散/收缩主题切换遮罩。
           由 useTheme().toggle(origin, buttonRef) 驱动，保证无论在桌面 header /
           移动端 drawer / admin header / oobe navbar 点击切换按钮，都只渲染同一份 mask，
           彻底避免多实例并发动画导致的白/黑屏一闪。 -->
      <ThemeRippleOverlay />

      <template #fallback>
        <!-- 与全局背景色一致的加载占位，避免首屏 CLS（布局抖动）。
             纯 div + 无外部依赖，SSR/客户端字节级完全一致。 -->
        <div
          class="min-h-screen w-full bg-background flex items-center justify-center"
          aria-hidden="true"
        >
          <div class="h-10 w-10 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
        </div>
      </template>
    </ClientOnly>
  </TooltipProvider>
</template>
