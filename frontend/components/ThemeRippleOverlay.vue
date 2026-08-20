<template>
  <!--
    仅作为「不支持 View Transition API」浏览器的兜底：
    一个简单的纯色遮罩，按 circle() 从点击点扩散/收缩。
    现代 Chrome / Edge / Safari 18+ 全部走 main.css 里的 ::view-transition-* 逻辑，
    浏览器自动对旧帧和新帧做「真实页面截图」，这里根本不会显示。
  -->
  <div
    v-if="state.visible"
    class="theme-ripple-overlay"
    :style="overlayStyle"
    aria-hidden="true"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeRipple } from '~~/composables/useTheme'

const { state, progress, fade } = useThemeRipple()

const overlayStyle = computed<Record<string, any>>(() => ({
  '--theme-ripple-progress': progress.value,
  '--theme-ripple-fade': fade.value,
  '--theme-ripple-maxr': state.maxRadius,
  '--theme-ripple-cx': state.cx + 'px',
  '--theme-ripple-cy': state.cy + 'px',
  backgroundColor: state.background
}))
</script>

<style scoped>
.theme-ripple-overlay {
  pointer-events: none;
  position: fixed;
  inset: 0;
  z-index: 99999;
  --theme-ripple-progress: 0;
  --theme-ripple-maxr: 2000;
  --theme-ripple-cx: 50vw;
  --theme-ripple-cy: 50vh;
  opacity: var(--theme-ripple-fade, 1);
  will-change: clip-path, -webkit-clip-path, opacity;
  clip-path: circle(
    calc(var(--theme-ripple-progress) * var(--theme-ripple-maxr) * 1px)
    at var(--theme-ripple-cx) var(--theme-ripple-cy)
  );
  -webkit-clip-path: circle(
    calc(var(--theme-ripple-progress) * var(--theme-ripple-maxr) * 1px)
    at var(--theme-ripple-cx) var(--theme-ripple-cy)
  );
  transition:
    clip-path 520ms cubic-bezier(0.22, 1, 0.36, 1),
    -webkit-clip-path 520ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 200ms ease;
}

@media (prefers-reduced-motion: reduce) {
  .theme-ripple-overlay {
    transition-duration: 1ms, 1ms, 1ms !important;
  }
}
</style>