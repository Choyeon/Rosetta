<script setup lang="ts">
import { computed } from 'vue'
import type { AdminUserTitle } from '~~/composables/useAdminManage'
import TitleIconSvg from '~~/components/TitleIconSvg.vue'

const props = withDefaults(defineProps<{
  title: AdminUserTitle | null | undefined
  size?: 'sm' | 'md' | 'lg'
  showName?: boolean
  showIcon?: boolean
  class?: string
}>(), {
  size: 'sm',
  showName: true,
  showIcon: true
})

const sizeCfg = {
  sm: { h: 'h-5', px: 'px-1.5', text: 'text-[10px]', gap: 'gap-1', iconSize: 'size-3' },
  md: { h: 'h-6', px: 'px-2', text: 'text-[11px]', gap: 'gap-1', iconSize: 'size-3.5' },
  lg: { h: 'h-7', px: 'px-2.5', text: 'text-xs', gap: 'gap-1.5', iconSize: 'size-4' }
}

const cfg = computed(() => sizeCfg[props.size])
const color = computed(() => props.title?.color || '#3b82f6')

const getLocalizedStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

const displayName = computed(() => getLocalizedStr(props.title?.name))
</script>

<template>
  <span
    v-if="title"
    :class="[
      'inline-flex items-center rounded-full border font-medium',
      cfg.h, cfg.px, cfg.text, cfg.gap,
      props.class
    ]"
    :style="{
      backgroundColor: `${color}18`,
      borderColor: `${color}40`,
      color: color
    }"
    :title="displayName"
  >
    <span
      v-if="showIcon"
      :class="[cfg.iconSize, 'flex items-center justify-center shrink-0']"
    >
      <TitleIconSvg
        v-if="title.icon"
        :icon="title.icon"
        :stroke-width="2"
      />
      <span
        v-else
        class="font-bold"
      >★</span>
    </span>
    <span
      v-if="showName"
      class="truncate max-w-[80px]"
    >{{ displayName }}</span>
  </span>
</template>
