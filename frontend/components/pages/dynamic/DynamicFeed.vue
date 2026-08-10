<!--
  DynamicFeed — 动态/说说列表容器
  props: items；slots: empty / footer
-->
<script setup lang="ts">
export interface DynamicItemData {
  id: string | number;
  author: { name: string; avatar?: string };
  content: string;
  createdAt: string;
  images?: string[];
  tags?: string[];
  likes?: number;
  comments?: number;
  reposts?: number;
  liked?: boolean;
}
interface Props {
  items: DynamicItemData[];
  loading?: boolean;
  hasMore?: boolean;
}
withDefaults(defineProps<Props>(), { items: () => [], loading: false, hasMore: true });
const emit = defineEmits<{ loadMore: []; like: [DynamicItemData] }>();
</script>

<template>
  <div class="space-y-md">
    <template v-if="!loading">
      <DynamicItem
        v-for="it in items"
        :key="it.id"
        :item="it"
        @like="emit('like', $event)"
      />
      <div v-if="!items.length" class="py-xl text-center text-neutral-text-tertiary text-sm bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary">
        <Icon name="material-symbols:bolt-rounded" class="w-10 h-10 mx-auto mb-sm opacity-40" />
        <slot name="empty">还没有动态，去发布第一条吧~</slot>
      </div>
    </template>
    <template v-else>
      <div v-for="i in 3" :key="i" class="bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary p-md animate-pulse">
        <div class="flex gap-sm">
          <div class="w-10 h-10 rounded-full bg-neutral-fill-hover" />
          <div class="flex-1 space-y-sm pt-1">
            <div class="h-4 w-1/4 bg-neutral-fill-hover rounded" />
            <div class="h-3 w-1/5 bg-neutral-fill-hover rounded" />
            <div class="h-4 w-full bg-neutral-fill-hover rounded" />
            <div class="h-4 w-5/6 bg-neutral-fill-hover rounded" />
            <div class="grid grid-cols-3 gap-xs"><div v-for="j in 3" :key="j" class="aspect-square bg-neutral-fill-hover rounded-lg" /></div>
          </div>
        </div>
      </div>
    </template>
    <div v-if="items.length && hasMore" class="text-center">
      <button
        type="button"
        class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-neutral-border-secondary text-sm text-neutral-text-secondary hover:text-primary-500 hover:border-primary-500 transition-colors duration-fast"
        :disabled="loading"
        @click="emit('loadMore')"
      >
        <Icon v-if="loading" name="material-symbols:progress-activity-rounded" class="w-4 h-4 animate-spin" />
        <Icon v-else name="material-symbols:expand-more-rounded" class="w-4 h-4" />
        加载更多
      </button>
    </div>
    <slot name="footer" />
  </div>
</template>
