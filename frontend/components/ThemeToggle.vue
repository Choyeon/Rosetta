<!--
  明暗切换按钮：点击把事件与按钮实例透传给 useTheme().toggle（圆形扩散动效需要源 DOM）。
  SSR 契约：isDark 首帧两端恒为 false（useState('theme-dark')），真实偏好由 plugins/theme.client.ts
  在 Hydrate 之后 apply，走 Vue patch 而非水合比对 —— 任何"首帧读 localStorage/matchMedia"
  的改动都会立刻造成大面积 mismatch。
-->
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
      data-icon="inline-start"
    />
    <Moon
      v-else
      data-icon="inline-start"
    />
  </Button>
</template>

<script setup lang="ts">
import { Button } from '~~/components/ui/button'
import { Sun, Moon } from '~~/lib/lucide-svg-icons'
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
