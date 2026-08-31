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
  <div :class="cn('flex flex-col gap-5 p-6', props.class)">
    <!-- 页头：标题 + 描述 + 操作区 -->
    <AdminPageHeader
      :title="title"
      :description="description"
    >
      <Badge
        v-if="count !== undefined"
        variant="secondary"
        class="rounded-[10px] px-3 py-1 bg-stone-100 text-stone-700 border-stone-200"
      >
        共 {{ count }} 项
      </Badge>
      <slot name="actions" />
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
