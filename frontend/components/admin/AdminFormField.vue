<!--
  后台表单字段包装：统一的 label（含必填星号）/ 控件 / 说明 / 错误四段式。
  ---------------------------------------------------------------------------
  旧表单的 label 有的写 text-xs text-muted-foreground、有的 text-sm、有的直接没有；
  必填标记、字段说明、校验错误的位置也各写一套。这里收敛成同一个垂直节奏
  （gap-1.5），错误优先于说明显示，避免两句同时出现把表单撑开。
-->
<script setup lang="ts">
import { Label } from '~~/components/ui/label'

withDefaults(defineProps<{
  label: string
  /** 关联控件 id（Label for） */
  for?: string
  hint?: string
  error?: string
  required?: boolean
}>(), {
  for: undefined,
  hint: undefined,
  error: undefined,
  required: false
})
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <Label
      :for="$props.for"
      class="flex items-center gap-1 text-sm font-medium text-foreground"
    >
      {{ label }}
      <span
        v-if="required"
        class="text-destructive"
        aria-hidden="true"
      >*</span>
      <span
        v-if="required"
        class="sr-only"
      >（必填）</span>
    </Label>
    <slot />
    <p
      v-if="error"
      class="text-xs leading-relaxed text-destructive"
    >
      {{ error }}
    </p>
    <p
      v-else-if="hint"
      class="text-xs leading-relaxed text-muted-foreground"
    >
      {{ hint }}
    </p>
  </div>
</template>
