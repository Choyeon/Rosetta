<!--
  AnimeDetailModal — 动漫详情抽屉/弹窗
  props: item；emits: close
  内容：封面大图 + 标题/评分/状态/简介/标签 + 剧集列表
-->
<script setup lang="ts">
import type { AnimeItem } from "./AnimeGrid.vue";

interface Props {
  item: AnimeItem | null;
  open: boolean;
}
defineProps<Props>();
const emit = defineEmits<{ "update:open": [boolean]; close: [] }>();

function close() {
  emit("update:open", false);
  emit("close");
}

const episodes = computed(() => {
  const total = props.item?.episodes?.total || props.item?.episodes?.current || 12;
  const cur = props.item?.episodes?.current || 0;
  return Array.from({ length: total }, (_, i) => ({
    n: i + 1,
    watched: i < cur,
  }));
});
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open && item"
        class="fixed inset-0 z-modal flex items-start sm:items-center justify-center p-4 sm:p-6 overflow-y-auto"
        @click.self="close"
      >
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" @click="close" />
        <div class="relative w-full max-w-3xl bg-neutral-bg-container rounded-2xl shadow-2xl border border-neutral-border-secondary overflow-hidden my-auto">
          <header class="relative h-56 sm:h-72 overflow-hidden">
            <NuxtImg
              v-if="item.cover"
              :src="item.cover"
              :alt="item.title"
              class="w-full h-full object-cover"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-neutral-bg-container via-neutral-bg-container/40 to-transparent" />
            <button
              type="button"
              class="absolute top-md right-md w-9 h-9 rounded-full bg-black/40 hover:bg-black/60 text-white backdrop-blur-sm transition-colors flex items-center justify-center"
              aria-label="关闭"
              @click="close"
            >
              <Icon name="material-symbols:close-rounded" class="w-5 h-5" />
            </button>
          </header>
          <div class="px-lg py-md -mt-12 relative">
            <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-md">
              <div class="min-w-0">
                <h2 class="text-xl sm:text-2xl font-bold text-neutral-text-primary leading-tight">{{ item.title }}</h2>
                <div class="mt-xs flex flex-wrap items-center gap-sm text-xs text-neutral-text-tertiary">
                  <span v-if="item.rating" class="inline-flex items-center gap-1 text-amber-500 font-semibold">
                    <Icon name="material-symbols:star-rounded" class="w-4 h-4" />
                    {{ Number(item.rating).toFixed(1) }}
                  </span>
                  <span v-if="item.episodes" class="inline-flex items-center gap-1">
                    <Icon name="material-symbols:ondemand-video-rounded" class="w-3.5 h-3.5" />
                    进度 {{ item.episodes.current || 0 }}<span v-if="item.episodes.total">/{{ item.episodes.total }}</span>
                  </span>
                  <span v-if="item.updatedAt">{{ dayjs(item.updatedAt).format("YYYY-MM-DD") }}</span>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button type="button" class="px-3 py-2 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 transition-colors">
                  <Icon name="material-symbols:play-arrow-rounded" class="w-4 h-4 inline align-middle -mt-0.5 mr-0.5" />
                  继续观看
                </button>
                <button type="button" class="px-3 py-2 rounded-lg border border-neutral-border-secondary text-sm hover:bg-neutral-fill-hover transition-colors text-neutral-text-secondary">
                  <Icon name="material-symbols:edit-rounded" class="w-4 h-4 inline align-middle -mt-0.5 mr-0.5" />
                  编辑
                </button>
              </div>
            </div>
            <div v-if="item.tags?.length" class="mt-md flex flex-wrap gap-1">
              <span
                v-for="t in item.tags"
                :key="t"
                class="text-xs px-2 py-0.5 rounded-full bg-primary-500/10 text-primary-500"
              >#{{ t }}</span>
            </div>
            <section class="mt-lg">
              <h3 class="text-sm font-semibold text-neutral-text-primary mb-xs flex items-center gap-1.5">
                <Icon name="material-symbols:menu-book-rounded" class="w-4 h-4 text-primary-500" />
                剧集列表
              </h3>
              <div class="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 gap-1">
                <button
                  v-for="ep in episodes"
                  :key="ep.n"
                  type="button"
                  class="aspect-square text-xs rounded-md border transition-all duration-fast"
                  :class="ep.watched ? 'bg-primary-500/10 text-primary-500 border-primary-500/30 font-medium' : 'text-neutral-text-secondary border-neutral-border-secondary hover:border-primary-500 hover:text-primary-500'"
                >
                  {{ ep.n }}
                </button>
              </div>
            </section>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 200ms ease; }
.modal-enter-active > div:last-child, .modal-leave-active > div:last-child { transition: transform 200ms ease, opacity 200ms ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from > div:last-child, .modal-leave-to > div:last-child { opacity: 0; transform: translateY(20px) scale(0.98); }
</style>
