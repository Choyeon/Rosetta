<script setup lang="ts">
import { computed } from 'vue'
import { getTitleIconDef } from '~~/composables/titleIcons'
import { resolveTitleIcon } from '~~/composables/titlePresets'

const props = withDefaults(defineProps<{
  icon?: string | null
  strokeWidth?: number
}>(), {
  strokeWidth: 2
})

const resolved = computed(() => {
  const r = resolveTitleIcon(props.icon)
  if (r.type === 'lucide') {
    return { kind: 'lucide' as const, def: getTitleIconDef(r.value) }
  }
  if (r.type === 'emoji') return { kind: 'emoji' as const, value: r.value }
  if (r.type === 'svg') return { kind: 'svg' as const, value: r.value }
  return { kind: 'empty' as const }
})
</script>

<template>
  <svg
    v-if="resolved.kind === 'lucide' && resolved.def"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
    :stroke-width="strokeWidth"
    class="size-full"
    aria-hidden="true"
  >
    <path
      v-for="(d, i) in resolved.def.paths"
      :key="i"
      :d="d"
    />
    <circle
      v-for="(c, i) in (resolved.def.circles ?? [])"
      :key="'c' + i"
      :cx="c.cx"
      :cy="c.cy"
      :r="c.r"
    />
  </svg>
  <svg
    v-else-if="resolved.kind === 'lucide'"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
    class="size-full"
  >
    <rect opacity="0" />
  </svg>
  <span
    v-else-if="resolved.kind === 'emoji'"
    style="font-size:inherit"
  >{{ resolved.value }}</span>
  <!-- eslint-disable-next-line vue/no-v-html -->
  <span
    v-else-if="resolved.kind === 'svg'"
    class="size-full flex items-center justify-center"
    v-html="resolved.value"
  />
</template>
