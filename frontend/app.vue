<script setup lang="ts">
import { Loader2 } from '@lucide/vue'
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
    <Suspense>
      <Transition name="page-fade" mode="out-in">
        <NuxtPage :key="route.fullPath" />
      </Transition>
      <template #fallback>
        <div class="flex items-center justify-center min-h-[50vh]">
          <div class="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/80 px-5 py-2 text-sm text-muted-foreground backdrop-blur animate-in">
            <Loader2 class="size-4 animate-spin" />
            Loading...
          </div>
        </div>
      </template>
    </Suspense>

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
