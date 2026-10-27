<!--
  后台表单分区卡片：标题区（图标 + 标题 + 说明 + 右侧操作）+ 内容区。
  ---------------------------------------------------------------------------
  用途：把「发布设置 / 可见性 / 分类与标签 / 封面 / SEO」这类长表单拆成可扫读的分区，
  避免一整张 AdminCard 里十几个 Label 平铺（文章编辑页旧版就是 8 个字段挤在一张卡里）。
  视觉与 AdminCard 同源（.card-surface），不引入新的皮肤；p-0 由本组件负责，
  内容区默认 p-5，调用方可传 body-class 覆盖。
-->
<script setup lang="ts">
import type { Component, HTMLAttributes } from 'vue'
import AdminCard from './AdminCard.vue'
import { cn } from '~~/lib/utils'

const props = withDefaults(defineProps<{
  title: string
  description?: string
  icon?: Component
  /** 内容区 class，默认 p-5 */
  bodyClass?: HTMLAttributes['class']
  class?: HTMLAttributes['class']
}>(), {
  description: undefined,
  icon: undefined,
  bodyClass: 'p-5',
  class: undefined
})
</script>

<template>
  <AdminCard :class="cn('p-0 overflow-hidden shrink-0', props.class)">
    <header class="flex items-start justify-between gap-3 border-b border-border/60 px-5 py-3.5">
      <div class="flex min-w-0 items-start gap-2.5">
        <div
          v-if="icon"
          class="size-8 shrink-0 rounded-lg bg-muted/60 text-muted-foreground flex items-center justify-center"
        >
          <component
            :is="icon"
            class="size-4"
          />
        </div>
        <div class="min-w-0">
          <h2 class="text-sm font-semibold tracking-tight leading-6">
            {{ title }}
          </h2>
          <p
            v-if="description"
            class="text-xs text-muted-foreground leading-relaxed"
          >
            {{ description }}
          </p>
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <slot name="actions" />
      </div>
    </header>
    <div :class="bodyClass">
      <slot />
    </div>
  </AdminCard>
</template>
