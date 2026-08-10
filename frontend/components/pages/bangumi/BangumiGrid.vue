<!--
  BangumiGrid — 番剧卡片网格（响应式）
  props: items、loading
-->
<script setup lang="ts">
export interface BangumiItem {
  id: string | number;
  name: string;
  nameCn?: string;
  image: string;
  score?: number;
  airDate?: string;
  totalEpisodes?: number;
  watchedEpisodes?: number;
  type?: "TV" | "MOVIE" | "OVA" | "WEB";
  status?: "watching" | "completed" | "plan";
  tags?: string[];
}
interface Props {
  items: BangumiItem[];
  loading?: boolean;
}
withDefaults(defineProps<Props>(), { items: () => [], loading: false });
defineEmits<{ open: [BangumiItem] }>();
</script>

<template>
  <div class="grid gap-sm sm:gap-md grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
    <template v-if="!loading">
      <BangumiCard
        v-for="it in items"
        :key="it.id"
        :item="it"
        @click="$emit('open', it)"
      />
      <div v-if="!items.length" class="col-span-full py-xl text-center text-neutral-text-tertiary text-sm">
        <Icon name="material-symbols:live-tv-outline-rounded" class="w-10 h-10 mx-auto mb-sm opacity-40" />
        暂无番剧数据
      </div>
    </template>
    <template v-else>
      <div v-for="i in 12" :key="i" class="rounded-xl border border-neutral-border-secondary bg-neutral-bg-container animate-pulse">
        <div class="aspect-[3/4] bg-neutral-fill-hover rounded-t-xl" />
        <div class="p-xs space-y-1">
          <div class="h-3.5 w-5/6 bg-neutral-fill-hover rounded" />
          <div class="h-3 w-2/3 bg-neutral-fill-hover rounded" />
        </div>
      </div>
    </template>
  </div>
</template>
