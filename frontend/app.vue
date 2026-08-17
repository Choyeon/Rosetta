<script setup lang="ts">
import { Toaster } from 'vue-sonner'
import { useI18n } from 'vue-i18n'
import { useTheme } from '~/composables/useTheme'
import { useScrollReveal } from '~/composables/useReadingUX'
import { useAuthStore } from '~~/stores/auth'

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

useHead({
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
})
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
  </NuxtLayout>
</template>
