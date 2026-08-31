<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'
import { Skeleton } from '~~/components/ui/skeleton'

const props = defineProps<{
  showIcon?: boolean
  class?: HTMLAttributes['class']
}>()

// 不要在这里用 Math.random() / computed 随机：SSR 与客户端渲染值不同会触发
// Hydration mismatch。骨架屏宽度固定即可，视觉差异足够。
const WIDTH = '72%'
</script>

<template>
  <div
    data-sidebar="menu-skeleton"
    :class="cn('rounded-md h-8 flex gap-2 px-2 items-center', props.class)"
  >
    <Skeleton
      v-if="showIcon"
      class="size-4 rounded-md"
      data-sidebar="menu-skeleton-icon"
    />

    <Skeleton
      class="h-4 flex-1 max-w-(--skeleton-width)"
      data-sidebar="menu-skeleton-text"
      :style="{ '--skeleton-width': WIDTH }"
    />
  </div>
</template>
