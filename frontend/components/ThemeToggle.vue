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

// SSR & 客户端首渲染 统一 isDark=false，由 useState('theme-dark', () => false) 保证字节级一致
// 用户偏好（localStorage / matchMedia）在 Hydrate 完成后由 plugins/theme.client.ts 异步 apply，
// 此时 Vue 走 patch，不触发 hydration mismatch。
const { t } = useI18n()
const { isDark, toggle } = useTheme()
const buttonRef = ref<InstanceType<typeof Button> | null>(null)

const handleToggle = (e: MouseEvent) => {
  toggle(e, buttonRef.value)
}
</script>
