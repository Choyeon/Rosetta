<!--
  AnimeCard — 动漫追番卡片
  props: item（封面 + 标题 + 状态 + 评分 + 进度 + 标签）
  悬浮阴影 + 封面渐变遮罩；状态徽章
-->
<script setup lang="ts">
import type { AnimeItem } from "./AnimeGrid.vue";

interface Props {
  item: AnimeItem;
}
defineProps<Props>();
defineEmits<{ click: [] }>();

const statusText: Record<AnimeItem["status"] & string, string> = {
  watching: "在看",
  completed: "已看",
  plan: "想看",
  "on-hold": "搁置",
  dropped: "弃坑",
};
const statusColor: Record<AnimeItem["status"] & string, string> = {
  watching: "bg-blue-500",
  completed: "bg-green-500",
  plan: "bg-violet-500",
  "on-hold": "bg-amber-500",
  dropped: "bg-rose-500",
};
</script>

<template>
  <article
    class="group bg-neutral-bg-container rounded-xl border border-neutral-border-secondary overflow-hidden shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-fast ease-out cursor-pointer"
    :aria-label="`动漫卡片 ${item.title}`"
    tabindex="0"
    @click="$emit('click')"
    @keyup.enter="$emit('click')"
  >
    <div class="relative aspect-[3/4] overflow-hidden bg-neutral-fill-hover">
      <NuxtImg
        v-if="item.cover"
        :src="item.cover"
        :alt="item.title"
        loading="lazy"
        class="w-full h-full object-cover transition-transform duration-slow ease-out group-hover:scale-105"
      />
      <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
      <div v-if="item.status" class="absolute top-xs left-xs">
        <span
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold text-white shadow"
          :class="statusColor[item.status] || 'bg-neutral-text-tertiary'"
        >
          <Icon v-if="item.status === 'watching'" name="material-symbols:play-arrow-rounded" class="w-3 h-3" />
          {{ statusText[item.status] || item.status }}
        </span>
      </div>
      <div v-if="item.rating" class="absolute top-xs right-xs flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-black/50 backdrop-blur-sm text-[10px] font-semibold text-amber-300">
        <Icon name="material-symbols:star-rounded" class="w-3 h-3" />
        {{ Number(item.rating).toFixed(1) }}
      </div>
      <div v-if="item.episodes" class="absolute bottom-xs left-xs right-xs text-[11px] text-white/95 font-medium">
        {{ item.episodes.current || 0 }}<span v-if="item.episodes.total"> / {{ item.episodes.total }}</span> 集
      </div>
    </div>
    <div class="p-sm space-y-xs">
      <h3 class="text-sm font-semibold text-neutral-text-primary line-clamp-1 leading-snug">{{ item.title }}</h3>
      <div v-if="item.tags?.length" class="flex flex-wrap gap-1">
        <span
          v-for="t in item.tags.slice(0, 3)"
          :key="t"
          class="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-fill-hover text-neutral-text-tertiary"
        >{{ t }}</span>
      </div>
    </div>
  </article>
</template>
