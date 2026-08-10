<!--
  BangumiCard — 单张番剧卡片
-->
<script setup lang="ts">
import type { BangumiItem } from "./BangumiGrid.vue";

interface Props { item: BangumiItem; }
defineProps<Props>();
defineEmits<{ click: [] }>();

const statusMap: Record<string, { text: string; cls: string }> = {
  watching: { text: "追番中", cls: "bg-blue-500" },
  completed: { text: "已看完", cls: "bg-green-500" },
  plan: { text: "想看", cls: "bg-violet-500" },
};
</script>

<template>
  <article
    class="group relative bg-neutral-bg-container rounded-xl border border-neutral-border-secondary overflow-hidden shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-fast ease-out cursor-pointer"
    tabindex="0"
    @click="$emit('click')"
    @keyup.enter="$emit('click')"
  >
    <div class="relative aspect-[3/4] overflow-hidden bg-neutral-fill-hover">
      <NuxtImg
        :src="item.image"
        :alt="item.nameCn || item.name"
        loading="lazy"
        class="w-full h-full object-cover transition-transform duration-slow ease-out group-hover:scale-105"
      />
      <div class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/0 to-transparent" />
      <div v-if="item.status && statusMap[item.status]" class="absolute top-xs left-xs">
        <span class="inline-block px-1.5 py-0.5 rounded-md text-[10px] font-semibold text-white shadow-sm" :class="statusMap[item.status].cls">
          {{ statusMap[item.status].text }}
        </span>
      </div>
      <div v-if="item.score" class="absolute top-xs right-xs inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-black/55 text-[10px] font-semibold text-amber-300 backdrop-blur-sm">
        <Icon name="material-symbols:star-rounded" class="w-3 h-3" />
        {{ Number(item.score).toFixed(1) }}
      </div>
      <div class="absolute bottom-xs left-xs right-xs text-[11px] text-white/95 leading-tight">
        <div class="line-clamp-2 font-semibold">{{ item.nameCn || item.name }}</div>
        <div v-if="(item.watchedEpisodes ?? item.totalEpisodes) !== undefined" class="mt-0.5 opacity-80">
          {{ item.watchedEpisodes || 0 }}<span v-if="item.totalEpisodes">/{{ item.totalEpisodes }}</span> 集
        </div>
      </div>
    </div>
    <div class="p-xs space-y-0.5">
      <div class="text-[11px] text-neutral-text-tertiary line-clamp-1">{{ item.name }}</div>
      <div class="flex items-center justify-between text-[10px] text-neutral-text-quaternary">
        <span v-if="item.airDate">{{ dayjs(item.airDate).format("YYYY") }}</span>
        <span v-if="item.type">{{ item.type }}</span>
      </div>
    </div>
  </article>
</template>
