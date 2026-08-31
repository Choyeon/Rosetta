<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
  /** 紧凑模式：更小的 padding，用于列表行等 */
  dense?: boolean
}>()
</script>

<template>
  <div
    :class="
      cn(
        'card-surface',
        props.dense ? 'p-3' : 'p-5',
        props.class
      )
    "
  >
    <slot />
  </div>
</template>
