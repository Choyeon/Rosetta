<script setup lang="ts">
import { computed } from 'vue'
import * as LucideIcons from '@lucide/vue'
import { resolveTitleIcon } from '~~/composables/titlePresets'
import type { AdminUserTitle } from '~~/composables/useAdminManage'

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
  sm: { h: 'h-4', px: 'px-1.5', text: 'text-[10px]', gap: 'gap-1', iconSize: 'size-2.5' },
  md: { h: 'h-5', px: 'px-2', text: 'text-[11px]', gap: 'gap-1', iconSize: 'size-3' },
  lg: { h: 'h-6', px: 'px-2.5', text: 'text-xs', gap: 'gap-1.5', iconSize: 'size-3.5' }
}

const cfg = computed(() => sizeCfg[props.size])
const color = computed(() => props.title?.color || '#3b82f6')
const renderedIcon = computed(() => resolveTitleIcon(props.title?.icon))

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
      v-if="showIcon && renderedIcon.type !== 'empty'"
      :class="[cfg.iconSize, 'flex items-center justify-center shrink-0']"
    >
      <component
        :is="(LucideIcons as Record<string, unknown>)[renderedIcon.value]"
        v-if="renderedIcon.type === 'lucide'"
        class="w-full h-full"
      />
      <span
        v-else-if="renderedIcon.type === 'emoji'"
        style="font-size:inherit"
      >{{ renderedIcon.value }}</span>
      <span
        v-else-if="renderedIcon.type === 'svg'"
        v-html="renderedIcon.value"
      />
    </span>
    <span
      v-else-if="showIcon"
      :class="[cfg.iconSize, 'flex items-center justify-center shrink-0 font-bold']"
    >
      ★
    </span>
    <span
      v-if="showName"
      class="truncate max-w-[80px]"
    >{{ displayName }}</span>
  </span>
</template>
