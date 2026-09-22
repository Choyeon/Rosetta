<script setup lang="ts">
/**
 * 后台统一页头 —— 全站唯一的页面标题区实现。
 *
 * 背景：此前每个 admin 页面各自手写标题区，导致 4 种并存样式：
 *   ① 图标方块 + text-xl        （tools/* 、system/* 共 11 个页面）
 *   ② 裸 text-2xl 无描述         （interaction/* 、media/* 、users/* 共 11 个页面）
 *   ③ AdminPageHeader（只有 AdminListPage 用过）
 *   ④ 根本不写标题区
 * 现在统一收敛到本组件，行为：
 *   - 传 icon → 渲染统一的图标方块（size-10 rounded-xl bg-primary）
 *   - 标题固定 text-xl / tracking-tight / font-bold（后台不是营销页，2xl 过大）
 *   - description 固定 text-sm text-muted-foreground
 *   - #actions 插槽统一右对齐，sm 以下自动换行
 *   - #meta 插槽用于计数 Badge 等与标题同行的辅助信息
 */
import type { Component, HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'

interface Props {
  title: string
  description?: string
  /** 图标组件（@lucide/vue 直接传入即可，如 Link2） */
  icon?: Component
  /** 图标方块配色，默认主色填充 */
  iconClass?: string
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <div :class="cn('flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between', props.class)">
    <div class="flex min-w-0 items-center gap-3">
      <div
        v-if="icon"
        class="size-10 shrink-0 rounded-xl flex items-center justify-center bg-primary text-primary-foreground shadow-sm"
        :class="props.iconClass"
      >
        <component
          :is="icon"
          class="size-5"
        />
      </div>
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
          <h1 class="text-xl font-bold tracking-tight leading-tight">
            {{ title }}
          </h1>
          <slot name="meta" />
        </div>
        <p
          v-if="description"
          class="mt-0.5 text-sm text-muted-foreground"
        >
          {{ description }}
        </p>
      </div>
    </div>
    <div class="flex shrink-0 flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
