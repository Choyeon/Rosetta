<script lang="ts" setup>
import type { HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <li
    role="presentation"
    aria-hidden="true"
    :class="cn('[&>svg]:w-3.5 [&>svg]:h-3.5', props.class)"
  >
    <slot>
      <!-- SSR 安全：原生 inline SVG ChevronRight -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        stroke="currentColor"
        class="size-4"
        aria-hidden="true"
      >
        <path d="m9 18 6-6-6-6" />
      </svg>
    </slot>
  </li>
</template>
