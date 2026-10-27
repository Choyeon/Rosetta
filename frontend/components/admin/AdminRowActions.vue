<!--
  后台行/卡片操作按钮组（列表页统一口径）。
  ---------------------------------------------------------------------------
  为什么要有它：此前每个列表页各行手写「编辑 / 删除」文字按钮，或者把图标按钮塞进
  opacity-0 group-hover:opacity-100 容器里——前者在操作列里挤成一排灰字、后者在触屏上
  根本点不到（没有 hover）。这里收敛为：
    · 永远可见（触屏/键盘都能操作）；
    · 36px 方形可点区（size="icon-sm"），不再用 h-7/w-7 覆写；
    · 每个按钮都有 Tooltip + aria-label（读屏与鼠标用户拿到同一个名称）；
    · 破坏性动作只走 destructive 令牌一套（text + hover 底色同源）。
  用法：
    <AdminRowActions :actions="[
      { key: 'edit', label: '编辑', icon: Pencil, onClick: () => openEdit(row) },
      { key: 'del', label: '删除', icon: Trash2, destructive: true, onClick: () => confirm(row.id) }
    ]" />
-->
<script setup lang="ts">
import type { Component } from 'vue'
import { Button } from '~~/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'

export interface AdminRowAction {
  /** 稳定 key（v-for） */
  key: string
  /** 悬停/读屏名称，同时作为 Tooltip 文案 */
  label: string
  icon: Component
  destructive?: boolean
  disabled?: boolean
  onClick: () => void
}

const props = withDefaults(defineProps<{
  actions: AdminRowAction[]
  /** 紧凑模式：无 Tooltip，仅保留 title（用于卡片角落等浮层场景） */
  compact?: boolean
}>(), {
  compact: false
})
</script>

<template>
  <div class="inline-flex items-center justify-end gap-0.5">
    <template
      v-for="action in props.actions"
      :key="action.key"
    >
      <Tooltip v-if="!props.compact">
        <TooltipTrigger as-child>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :class="action.destructive
              ? 'text-destructive hover:text-destructive hover:bg-destructive-muted'
              : 'text-muted-foreground hover:text-foreground'"
            :aria-label="action.label"
            :disabled="action.disabled"
            @click.stop="action.onClick"
          >
            <component
              :is="action.icon"
              data-icon="inline-start"
            />
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          {{ action.label }}
        </TooltipContent>
      </Tooltip>
      <Button
        v-else
        type="button"
        variant="ghost"
        size="icon-sm"
        :class="action.destructive
          ? 'text-destructive hover:text-destructive hover:bg-destructive-muted'
          : 'text-muted-foreground hover:text-foreground'"
        :title="action.label"
        :aria-label="action.label"
        :disabled="action.disabled"
        @click.stop="action.onClick"
      >
        <component
          :is="action.icon"
          data-icon="inline-start"
        />
      </Button>
    </template>
  </div>
</template>
