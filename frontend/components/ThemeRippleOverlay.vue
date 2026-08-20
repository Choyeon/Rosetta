<template>
  <div
    v-if="state.visible"
    class="theme-ripple-overlay"
    :style="{
      background: state.background,
      '--theme-ripple-progress': progress,
      '--theme-ripple-fade': fade,
      '--theme-ripple-maxr': state.maxRadius,
      '--theme-ripple-cx': state.cx + 'px',
      '--theme-ripple-cy': state.cy + 'px'
    } as any"
    aria-hidden="true"
  />
</template>

<script setup lang="ts">
import { useThemeRipple } from '~~/composables/useTheme'
const { state, progress, fade } = useThemeRipple()
</script>
