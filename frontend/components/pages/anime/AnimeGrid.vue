<!--
  AnimeGrid — 动漫追番网格容器
  props: items（AnimeCard 数据数组）、columns（响应式栅格列数默认值）
  slots: empty（空状态）、header（标题区）
-->
<script setup lang="ts">
export interface AnimeItem {
  id: string | number;
  title: string;
  cover: string;
  status?: "watching" | "completed" | "plan" | "on-hold" | "dropped";
  rating?: number;
  episodes?: { current: number; total?: number };
  tags?: string[];
  updatedAt?: string;
}
interface Props {
  items: AnimeItem[];
  loading?: boolean;
  columns?: { sm: number; md: number; lg: number; xl: number };
}
withDefaults(defineProps<Props>(), {
  items: () => [],
  loading: false,
  columns: () => ({ sm: 2, md: 3, lg: 4, xl: 5 }),
});

const emit = defineEmits<{ open: [item: AnimeItem] }>();
</script>

<template>
  <div>
    <div
      class="grid gap-md"
      :style="{
        gridTemplateColumns: `repeat(${columns.sm}, minmax(0, 1fr))`,
      }"
    >
      <template v-if="!loading">
        <AnimeCard
          v-for="it in items"
          :key="it.id"
          :item="it"
          @click="emit('open', it)"
        />
        <div v-if="!items.length" class="col-span-full py-xl text-center text-neutral-text-tertiary text-sm">
          <Icon name="material-symbols:movie-outline-rounded" class="w-10 h-10 mx-auto mb-sm opacity-40" />
          <slot name="empty">暂无追番记录</slot>
        </div>
      </template>
      <template v-else>
        <div v-for="i in 10" :key="i" class="bg-neutral-bg-container rounded-xl border border-neutral-border-secondary animate-pulse">
          <div class="aspect-[3/4] bg-neutral-fill-hover rounded-t-xl" />
          <div class="p-sm space-y-1">
            <div class="h-4 w-3/4 bg-neutral-fill-hover rounded" />
            <div class="h-3 w-1/2 bg-neutral-fill-hover rounded" />
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
