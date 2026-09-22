<script lang="ts" setup>
import type { HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <span
    role="presentation"
    aria-hidden="true"
    :class="cn('flex h-9 w-9 items-center justify-center', props.class)"
  >
    <slot>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        stroke="currentColor"
        class="h-4 w-4"
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="12"
          r="1"
        /><circle
          cx="19"
          cy="12"
          r="1"
        /><circle
          cx="5"
          cy="12"
          r="1"
        />
      </svg>
    </slot>
    <span class="sr-only">More</span>
  </span>
</template>
