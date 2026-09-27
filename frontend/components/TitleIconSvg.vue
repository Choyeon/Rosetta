<!--
  称号图标渲染器：icon 字段只接受预设 ID 或 emoji，预设真源是 composables/titleIcons.ts
  与 titlePresets.ts（新增图标要在两处登记）。
  安全红线：这里没有 v-html 分支 —— 曾有的内联 SVG 直出被确认为存储型 XSS 通道已删除，
  恢复它等于让 DB 脏数据绕过 §12.8；未知 ID 走透明矩形兜底而不是回显原始字符串。
-->
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
  <!--
    这里没有 v-html 分支：称号图标只允许预设 ID 与 emoji。
    内联 SVG 曾经过 v-html 渲染（resolveTitleIcon 的 'svg' 分支），属存储型 XSS 通道，已移除。
  -->
</template>
