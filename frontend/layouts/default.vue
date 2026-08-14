<script setup lang="ts">
import { TooltipProvider } from '~~/components/ui/tooltip'
import AppHeader from '~~/components/AppHeader.vue'
import AppFooter from '~~/components/AppFooter.vue'
import { useTheme } from '~~/composables/useTheme'
import { useAuthStore } from '~~/stores/auth'

useTheme()
const authStore = useAuthStore()

onMounted(() => {
  authStore.initialize()
})
</script>

<template>
  <div class="min-h-screen bg-background font-sans antialiased flex flex-col">
    <TooltipProvider :delay-duration="0">
      <AppHeader />
      <main id="main-content" class="flex-1">
        <slot />
      </main>
      <AppFooter />
    </TooltipProvider>
  </div>
</template>
