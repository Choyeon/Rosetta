<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import { cn } from '~~/lib/utils'

interface ProgressProps {
  value?: number
  max?: number
  class?: HTMLAttributes['class']
  indicatorClass?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<ProgressProps>(), {
  value: 0,
  max: 100
})

const percentage = computed(() => {
  const max = Math.max(1, props.max)
  const v = Math.min(max, Math.max(0, props.value))
  return (v / max) * 100
})
</script>

<template>
  <div
    role="progressbar"
    :aria-valuemin="0"
    :aria-valuemax="max"
    :aria-valuenow="value"
    :class="cn('relative h-2 w-full overflow-hidden rounded-full bg-muted', props.class)"
  >
    <div
      :class="cn('h-full w-full flex-1 bg-primary transition-all duration-300 ease-out', props.indicatorClass)"
      :style="{ transform: `translateX(-${100 - percentage}%)` }"
    />
  </div>
</template>
