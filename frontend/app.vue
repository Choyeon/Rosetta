<script setup lang="ts">
import { Toaster } from 'vue-sonner'
import { useI18n } from 'vue-i18n'
import { useTheme } from '~/composables/useTheme'
import { useScrollReveal } from '~/composables/useReadingUX'
import { useAuthStore } from '~~/stores/auth'
import ThemeRippleOverlay from '~~/components/ThemeRippleOverlay.vue'

const route = useRoute()
const { locale } = useI18n()
useTheme()
useScrollReveal()

const authStore = useAuthStore()

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
  <!-- eslint-disable-next-line vue/no-deprecated-filter -- TS 联合类型的 | 被规则误判为 Vue2 filter -->
  <NuxtLayout :name="(route.meta.layout ?? 'default') as 'default' | false">
    <!-- 页面过渡由 nuxt.config 的 app.pageTransition 驱动（Nuxt 原生机制）。
         不要在此手动包裹 <Transition> / <Suspense>：旧结构在链式重定向时
         out-in 过渡与异步页面组件相互等待，导致渲染管线静默死锁（页面空白）。 -->
    <NuxtPage />

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
  </NuxtLayout>
</template>
