<template>
  <Button
    ref="buttonRef"
    variant="ghost"
    size="icon"
    :aria-label="isDark ? (t('common.themeDark') || '切换为亮色模式') : (t('common.themeLight') || '切换为暗色模式')"
    class="relative overflow-hidden"
    @click="handleToggle"
  >
    <Sun
      v-if="isDark"
      class="size-5"
    />
    <Moon
      v-else
      class="size-5"
    />
  </Button>
</template>

<script setup lang="ts">
import { Button } from '~~/components/ui/button'
import { Sun, Moon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '~~/composables/useTheme'

const { t } = useI18n()
const { isDark, toggle } = useTheme()
const buttonRef = ref<InstanceType<typeof Button> | null>(null)

const handleToggle = (e: MouseEvent) => {
  toggle(e, buttonRef.value)
}
</script>
