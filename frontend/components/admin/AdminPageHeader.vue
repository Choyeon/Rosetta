<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'

interface Props {
  title: string
  description?: string
  class?: HTMLAttributes['class']
}

defineProps<Props>()
</script>

<template>
  <div :class="cn('flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between', $props.class)">
    <div class="flex flex-col gap-1">
      <h1 class="text-2xl font-bold tracking-tight">
        {{ title }}
      </h1>
      <p
        v-if="description"
        class="text-sm text-muted-foreground"
      >
        {{ description }}
      </p>
    </div>
    <div class="flex items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
