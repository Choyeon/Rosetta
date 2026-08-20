<script setup lang="ts">
import { TooltipProvider } from '~~/components/ui/tooltip'
import AppHeader from '~~/components/AppHeader.vue'
import AppFooter from '~~/components/AppFooter.vue'
import { useTheme } from '~~/composables/useTheme'
import { useAuthStore } from '~~/stores/auth'

// 初始化 useTheme 共享状态（不调用任何会影响首渲染 DOM 的逻辑；真实偏好延后到 Hydrate 后）
useTheme()
const authStore = useAuthStore()

// 保证 SSR & 客户端首渲染 使用同一份从后端拉到的站点配置
// （避免 AppHeader 里 brandName SSR="Rosetta" / 客户端="Rosetta Blog" 的文本 mismatch）
const site = useSite()
await site.ensureLoaded()

onMounted(() => {
  authStore.initialize()
})
</script>

<template>
  <div class="min-h-screen bg-background font-sans antialiased flex flex-col">
    <TooltipProvider :delay-duration="0">
      <AppHeader />
      <main
        id="main-content"
        class="flex-1"
      >
        <slot />
      </main>
      <AppFooter />
    </TooltipProvider>
  </div>
</template>
