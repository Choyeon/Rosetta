<!--
  PostMeta — 文章元信息（作者 / 分类 / 发布时间 / 阅读时长）
-->
<script setup lang="ts">
import type { Post } from "./PostCard.vue";

interface Props {
  post: Post;
  compact?: boolean;
  showAuthor?: boolean;
  showCategory?: boolean;
  showDate?: boolean;
  showReadingTime?: boolean;
}
withDefaults(defineProps<Props>(), {
  compact: false,
  showAuthor: true,
  showCategory: true,
  showDate: true,
  showReadingTime: true,
});
</script>

<template>
  <div
    class="flex items-center flex-wrap gap-xs"
    :class="compact ? 'text-[10px] text-neutral-text-quaternary' : 'text-xs text-neutral-text-tertiary'"
  >
    <template v-if="showAuthor">
      <div v-if="post.author" class="inline-flex items-center gap-1">
        <div class="w-4 h-4 rounded-full overflow-hidden bg-gradient-to-br from-primary-300 to-rosetta-nebula flex items-center justify-center text-white text-[9px] font-semibold flex-shrink-0">
          <NuxtImg v-if="post.author.avatar" :src="post.author.avatar" :alt="post.author.name" class="w-full h-full object-cover" />
          <span v-else>{{ (post.author.name || "?").slice(0, 1) }}</span>
        </div>
        <span class="line-clamp-1">{{ post.author.name }}</span>
      </div>
    </template>
    <span v-if="showCategory && post.category" class="inline-flex items-center gap-0.5">
      <Icon name="material-symbols:folder-rounded" :class="compact ? 'w-2.5 h-2.5' : 'w-3 h-3'" />
      <span>{{ post.category }}</span>
    </span>
    <time v-if="showDate && post.published" :datetime="post.published" class="inline-flex items-center gap-0.5">
      <Icon name="material-symbols:schedule-rounded" :class="compact ? 'w-2.5 h-2.5' : 'w-3 h-3'" />
      {{ dayjs(post.published).format(compact ? "MM-DD" : "YYYY-MM-DD") }}
    </time>
    <span v-if="showReadingTime && post.readingTime" class="inline-flex items-center gap-0.5">
      <Icon name="material-symbols:menu-book-rounded" :class="compact ? 'w-2.5 h-2.5' : 'w-3 h-3'" />
      {{ post.readingTime }} 分钟
    </span>
  </div>
</template>
