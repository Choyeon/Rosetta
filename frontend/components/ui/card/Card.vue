<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <div
    :class="
      cn(
        'card-surface lift-hover overflow-hidden text-card-foreground',
        props.class
      )
    "
  >
    <slot />
  </div>
</template>
