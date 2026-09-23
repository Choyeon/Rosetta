<template>
  <div class="container py-16 max-w-2xl">
    <header class="mb-10">
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('settings.title') }}
      </h1>
      <p class="text-muted-foreground mt-2">
        {{ t('settings.desc') }}
      </p>
    </header>

    <Card>
      <CardHeader>
        <CardTitle class="flex items-center gap-2 text-lg">
          <MonitorDot data-icon="inline-start" />
          {{ t('settings.display') }}
        </CardTitle>
        <CardDescription>
          {{ t('settings.displayDesc') }}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          role="radiogroup"
          :aria-label="t('settings.themeMode')"
          class="grid grid-cols-1 sm:grid-cols-3 gap-3"
        >
          <Button
            v-for="opt in modeOptions"
            :key="opt.value"
            :variant="pref === opt.value ? 'default' : 'outline'"
            class="justify-start h-auto py-3 px-4"
            role="radio"
            :aria-checked="pref === opt.value"
            @click="applyOption(opt.value)"
          >
            <component
              :is="opt.icon"
              data-icon="inline-start"
            />
            <span>
              <span class="block font-medium text-sm">{{ opt.label }}</span>
              <span class="block text-xs text-muted-foreground mt-0.5">{{ opt.hint }}</span>
            </span>
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { MonitorDot, Sun, Moon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '~~/composables/useTheme'
import { useSeo } from '~~/composables/useSeo'

definePageMeta({ layout: 'default', ssr: false })

type ThemePref = 'system' | 'light' | 'dark'

const { t } = useI18n()
const { setLight, setDark, setSystem } = useTheme()

// 偏好真值在 localStorage（'theme'）；SSR 关闭（ssr:false），onMounted 读取安全。
const pref = ref<ThemePref>('light')

const modeOptions = computed(() => [
  { value: 'system' as const, icon: MonitorDot, label: t('settings.modeSystem'), hint: t('settings.modeSystemHint') },
  { value: 'light' as const, icon: Sun, label: t('settings.modeLight'), hint: t('settings.modeLightHint') },
  { value: 'dark' as const, icon: Moon, label: t('settings.modeDark'), hint: t('settings.modeDarkHint') }
])

const applyOption = (mode: ThemePref) => {
  pref.value = mode
  if (mode === 'dark') setDark()
  else if (mode === 'light') setLight()
  else setSystem()
}

onMounted(() => {
  try {
    const stored = localStorage.getItem('theme')
    pref.value = stored === 'dark' || stored === 'system' ? stored : 'light'
  } catch {
    pref.value = 'light'
  }
})

useSeo({
  title: computed(() => String(t('settings.title'))),
  description: computed(() => String(t('settings.desc'))),
  type: 'website'
})
</script>
