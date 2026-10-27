<!--
  Admin 指标格：标签 + 单值 + 可选单位，用于监控/性能类页格里成排展示的读数。
  口径：`display` 优先于 `value`，`value` 非有限数一律回 `—`——"没取到"和"真的是 0"必须区分，
  否则接口失败时整排指标会伪装成一台满负荷为零的机器。
-->
<template>
  <div class="rounded-xl border border-border/60 px-4 py-3">
    <p class="text-xs text-muted-foreground">
      {{ label }}
    </p>
    <p class="text-xl font-bold tabular-nums tracking-tight">
      {{ shown }}<span
        v-if="unit && shown !== '—'"
        class="text-xs font-normal text-muted-foreground ml-0.5"
      >{{ unit }}</span>
    </p>
    <p
      v-if="note"
      class="text-[11px] text-muted-foreground mt-0.5"
    >
      {{ note }}
    </p>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  value?: number | string | null
  /** 已格式化好的文本读数（如 `128 MB`），优先于 value。 */
  display?: string | null
  unit?: string
  note?: string
}>(), {
  value: null,
  display: null,
  unit: '',
  note: ''
})

const shown = computed(() => {
  if (props.display !== null && props.display !== '') return props.display
  if (props.value === null || props.value === undefined || props.value === '') return '—'
  const n = Number(props.value)
  if (!Number.isFinite(n)) return String(props.value)
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
})
</script>
