<!--
  列表页骨架 = AdminPageHeader + #toolbar + AdminCard(`p-0 overflow-hidden`，靠 twMerge 压掉默认 p-5) + #pagination。
  消费方是 pages/admin/content/ 下 5 个页面；本组件不转发 icon，带图标的页头（tools/system 等）直接用 AdminPageHeader。
  插槽契约：AdminPageHeader 只暴露 #meta / #actions 两个具名出口，没有 default 插槽——页头内容必须以
  <template #meta>/<template #actions> 传入，裸子节点会整体不渲染（曾因此让 5 个列表页的计数徽标与
  「新建」按钮全部消失）。
-->
<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'
import AdminCard from './AdminCard.vue'

interface Props {
  title: string
  description?: string
  /** 数据总数（用于标题旁的计数徽标） */
  count?: number
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <div :class="cn('flex flex-col gap-5', props.class)">
    <!-- 页头：标题 + 计数徽标（#meta）+ 操作区（#actions）。
         AdminPageHeader 只有具名出口，写成裸子节点会被编译进它并不存在的 default 插槽而整体丢失。 -->
    <AdminPageHeader
      :title="title"
      :description="description"
    >
      <template #meta>
        <Badge
          v-if="count !== undefined"
          variant="secondary"
          class="rounded-[10px] px-3 py-1 bg-stone-100 text-stone-700 border-stone-200"
        >
          共 {{ count }} 项
        </Badge>
      </template>
      <template #actions>
        <slot name="actions" />
      </template>
    </AdminPageHeader>

    <!-- 工具栏（搜索 / 筛选 / 批量操作） -->
    <slot name="toolbar" />

    <!-- 内容卡片（AdminCard 无 hover 效果，用于列表页面） -->
    <AdminCard class="p-0 overflow-hidden">
      <slot />
    </AdminCard>

    <!-- 分页（可选） -->
    <slot name="pagination" />
  </div>
</template>
