<template>
  <template v-if="state.visible">
    <!-- 底层：旧主题全屏截图 → 锁定整个屏幕，避免真实 DOM 切类时产生的瞬态被用户看到；
         截图为空时回落到目标主题纯色（极端情况下退化到之前的效果） -->
    <div
      class="theme-ripple-backdrop"
      :style="backdropStyle"
      aria-hidden="true"
    />
    <!-- 上层：新主题全屏截图，但仅在 circle 揭示区域内可见。
         圆外是 before（旧主题），圆内是 after（新主题），动画期间从头到尾都是真实页面内容，
         不会像纯色 mask 那样出现整个屏幕纯黑/纯白的感觉。 -->
    <div
      class="theme-ripple-foreground"
      :style="foregroundStyle"
      aria-hidden="true"
    />
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeRipple } from '~~/composables/useTheme'

const { state, progress, fade } = useThemeRipple()

const commonVars = computed(() => ({
  '--theme-ripple-progress': progress.value,
  '--theme-ripple-fade': fade.value,
  '--theme-ripple-maxr': state.maxRadius,
  '--theme-ripple-cx': state.cx + 'px',
  '--theme-ripple-cy': state.cy + 'px'
}))

const backdropStyle = computed<Record<string, any>>(() => {
  const vars = commonVars.value as Record<string, any>
  if (state.beforeImage) {
    vars.backgroundImage = `url("${state.beforeImage}")`
    vars.backgroundRepeat = 'no-repeat'
    vars.backgroundPosition = 'left top'
    vars.backgroundSize = '100% 100%'
    vars.backgroundColor = state.background
  } else {
    vars.backgroundColor = state.background
  }
  return vars
})

const foregroundStyle = computed<Record<string, any>>(() => {
  const vars = commonVars.value as Record<string, any>
  if (state.afterImage) {
    vars.backgroundImage = `url("${state.afterImage}")`
    vars.backgroundRepeat = 'no-repeat'
    vars.backgroundPosition = 'left top'
    vars.backgroundSize = '100% 100%'
    vars.backgroundColor = state.background
  } else {
    vars.backgroundColor = state.background
  }
  return vars
})
</script>

<style scoped>
.theme-ripple-backdrop,
.theme-ripple-foreground {
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
  transition:
    clip-path 960ms cubic-bezier(0.22, 1, 0.36, 1),
    -webkit-clip-path 960ms cubic-bezier(0.22, 1, 0.36, 1),
    --theme-ripple-progress 960ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease,
    --theme-ripple-fade 220ms ease;
}

.theme-ripple-foreground {
  z-index: 100000;
  clip-path: circle(
    calc(var(--theme-ripple-progress) * var(--theme-ripple-maxr) * 1px)
    at var(--theme-ripple-cx) var(--theme-ripple-cy)
  );
  -webkit-clip-path: circle(
    calc(var(--theme-ripple-progress) * var(--theme-ripple-maxr) * 1px)
    at var(--theme-ripple-cx) var(--theme-ripple-cy)
  );
}

.theme-ripple-backdrop {
  /* 整屏铺住 before 截图，不需要 clip，它只是“冻结旧画面” */
  clip-path: none;
  -webkit-clip-path: none;
}

@media (prefers-reduced-motion: reduce) {
  .theme-ripple-backdrop,
  .theme-ripple-foreground {
    transition-duration: 1ms, 1ms, 1ms, 1ms, 1ms !important;
  }
}
</style>
