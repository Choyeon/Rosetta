<!--
  DynamicItem — 单条动态/说说卡片
  头像 + 昵称时间 + 内容富文本 + 图集（DynamicGallery）+ 操作栏（赞/评/转）
-->
<script setup lang="ts">
import type { DynamicItemData } from "./DynamicFeed.vue";

interface Props { item: DynamicItemData; }
defineProps<Props>();
const emit = defineEmits<{ like: [DynamicItemData] }>();
</script>

<template>
  <article class="bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary shadow-sm overflow-hidden">
    <header class="p-md pb-xs flex items-center gap-sm">
      <div class="w-10 h-10 rounded-full overflow-hidden flex-shrink-0 bg-gradient-to-br from-primary-300 to-rosetta-nebula flex items-center justify-center text-white font-semibold">
        <NuxtImg v-if="item.author.avatar" :src="item.author.avatar" :alt="item.author.name" class="w-full h-full object-cover" loading="lazy" />
        <span v-else>{{ (item.author.name || "U").slice(0, 1) }}</span>
      </div>
      <div class="flex-1 min-w-0">
        <div class="text-sm font-semibold text-neutral-text-primary line-clamp-1">{{ item.author.name }}</div>
        <div class="text-xs text-neutral-text-tertiary flex items-center gap-1">
          <Icon name="material-symbols:schedule-rounded" class="w-3 h-3" />
          <time :datetime="item.createdAt">{{ dayjs(item.createdAt).fromNow() }}</time>
        </div>
      </div>
      <button type="button" class="w-8 h-8 rounded-md text-neutral-text-tertiary hover:bg-neutral-fill-hover hover:text-neutral-text-secondary transition-colors flex items-center justify-center" aria-label="更多">
        <Icon name="material-symbols:more-horiz-rounded" class="w-4 h-4" />
      </button>
    </header>
    <div class="px-md pb-sm">
      <p class="text-sm leading-relaxed text-neutral-text-primary whitespace-pre-wrap break-words">{{ item.content }}</p>
      <div v-if="item.tags?.length" class="mt-xs flex flex-wrap gap-1">
        <span v-for="t in item.tags" :key="t" class="text-xs px-2 py-0.5 rounded-full bg-primary-500/10 text-primary-500">#{{ t }}</span>
      </div>
    </div>
    <div v-if="item.images?.length" class="px-md pb-sm">
      <DynamicGallery :images="item.images" />
    </div>
    <footer class="border-t border-neutral-border-secondary flex items-center divide-x divide-neutral-border-secondary text-xs">
      <button
        type="button"
        class="flex-1 inline-flex items-center justify-center gap-1.5 py-sm transition-colors duration-fast"
        :class="item.liked ? 'text-rose-500' : 'text-neutral-text-secondary hover:text-rose-500 hover:bg-neutral-fill-hover'"
        @click="emit('like', item)"
      >
        <Icon :name="item.liked ? 'material-symbols:favorite-rounded' : 'material-symbols:favorite-outline-rounded'" class="w-4 h-4" />
        <span class="font-medium">{{ item.likes || 0 }}</span>
      </button>
      <button
        type="button"
        class="flex-1 inline-flex items-center justify-center gap-1.5 py-sm text-neutral-text-secondary hover:text-primary-500 hover:bg-neutral-fill-hover transition-colors"
      >
        <Icon name="material-symbols:mode-comment-outline-rounded" class="w-4 h-4" />
        <span class="font-medium">{{ item.comments || 0 }}</span>
      </button>
      <button
        type="button"
        class="flex-1 inline-flex items-center justify-center gap-1.5 py-sm text-neutral-text-secondary hover:text-emerald-500 hover:bg-neutral-fill-hover transition-colors"
      >
        <Icon name="material-symbols:repeat-rounded" class="w-4 h-4" />
        <span class="font-medium">{{ item.reposts || 0 }}</span>
      </button>
      <button
        type="button"
        class="flex-1 inline-flex items-center justify-center gap-1.5 py-sm text-neutral-text-secondary hover:text-amber-500 hover:bg-neutral-fill-hover transition-colors"
      >
        <Icon name="material-symbols:share-rounded" class="w-4 h-4" />
      </button>
    </footer>
    <DynamicInlineComments />
  </article>
</template>
