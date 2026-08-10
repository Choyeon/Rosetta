<!--
  PostStats — 文章统计数据（浏览 / 点赞 / 评论 / 字数）
  props: post / compact
-->
<script setup lang="ts">
import type { Post } from "./PostCard.vue";

interface Props {
  post: Post;
  compact?: boolean;
  showViews?: boolean;
  showLikes?: boolean;
  showComments?: boolean;
  showWords?: boolean;
  wordsCount?: number;
}
withDefaults(defineProps<Props>(), {
  compact: false,
  showViews: true,
  showLikes: true,
  showComments: true,
  showWords: false,
  wordsCount: 0,
});
</script>

<template>
  <div
    class="flex items-center gap-sm"
    :class="compact ? 'text-[10px] text-neutral-text-quaternary' : 'text-xs text-neutral-text-tertiary'"
  >
    <span v-if="showViews && (post.views ?? 0) >= 0" class="inline-flex items-center gap-0.5">
      <Icon name="material-symbols:visibility-rounded" :class="compact ? 'w-2.5 h-2.5' : 'w-3 h-3'" />
      {{ (post.views || 0).toLocaleString() }}
    </span>
    <span v-if="showLikes && (post.likes ?? 0) >= 0" class="inline-flex items-center gap-0.5">
      <Icon name="material-symbols:favorite-outline-rounded" :class="compact ? 'w-2.5 h-2.5' : 'w-3 h-3'" />
      {{ post.likes || 0 }}
    </span>
    <span v-if="showComments && (post.comments ?? 0) >= 0" class="inline-flex items-center gap-0.5">
      <Icon name="material-symbols:mode-comment-outline-rounded" :class="compact ? 'w-2.5 h-2.5' : 'w-3 h-3'" />
      {{ post.comments || 0 }}
    </span>
    <span v-if="showWords && wordsCount > 0" class="inline-flex items-center gap-0.5">
      <Icon name="material-symbols:edit-note-rounded" :class="compact ? 'w-2.5 h-2.5' : 'w-3 h-3'" />
      {{ wordsCount.toLocaleString() }} 字
    </span>
  </div>
</template>
