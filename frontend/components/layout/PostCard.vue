<!--
  PostCard — 通用文章列表卡片（横向 / 纵向自适应）
  props: post + variant（'card' | 'row' | 'compact'）
-->
<script setup lang="ts">
export interface Post {
  _path: string;
  title: string;
  description?: string;
  image?: string;
  category?: string;
  tags?: string[];
  author?: { name: string; avatar?: string };
  published?: string;
  readingTime?: number;
  views?: number;
  likes?: number;
  comments?: number;
  pinned?: boolean;
  draft?: boolean;
}
interface Props {
  post: Post;
  variant?: "card" | "row" | "compact";
}
withDefaults(defineProps<Props>(), { variant: "card" });
</script>

<template>
  <NuxtLink
    :to="post._path"
    class="group block bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary overflow-hidden shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-fast ease-out"
    :class="{ 'flex flex-col': variant !== 'row', 'flex flex-row': variant === 'row' }"
  >
    <!-- 封面 -->
    <div
      class="relative overflow-hidden bg-gradient-to-br from-primary-400/20 via-primary-500/5 to-rosetta-gold/20 flex-shrink-0"
      :class="[
        variant === 'row' ? 'w-48 md:w-64 aspect-[4/3]' : 'aspect-[16/9]',
        variant === 'compact' ? 'hidden sm:block sm:aspect-[16/9]' : '',
      ]"
    >
      <NuxtImg
        v-if="post.image"
        :src="post.image"
        :alt="post.title"
        loading="lazy"
        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        class="w-full h-full object-cover transition-transform duration-slow ease-out group-hover:scale-105"
      />
      <div v-else class="absolute inset-0 flex items-center justify-center text-primary-500/30">
        <Icon name="material-symbols:article-rounded" class="w-14 h-14" />
      </div>
      <div class="absolute top-xs left-xs flex items-center gap-1 flex-wrap">
        <span
          v-if="post.pinned"
          class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-rose-500 text-white text-[10px] font-semibold shadow-sm"
        >
          <Icon name="material-symbols:push-pin-rounded" class="w-3 h-3" />
          置顶
        </span>
        <span
          v-if="post.draft"
          class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-amber-500 text-white text-[10px] font-semibold shadow-sm"
        >
          草稿
        </span>
        <NuxtLink
          v-if="post.category"
          :to="`/categories/${post.category}`"
          class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-black/50 backdrop-blur-sm text-white text-[10px] font-medium no-underline"
          @click.stop
        >
          <Icon name="material-symbols:folder-rounded" class="w-3 h-3" />
          {{ post.category }}
        </NuxtLink>
      </div>
    </div>
    <!-- 正文 -->
    <div class="p-md flex flex-col flex-1 min-h-0">
      <h3
        class="font-semibold text-neutral-text-primary line-clamp-2 group-hover:text-primary-500 transition-colors leading-snug"
        :class="variant === 'compact' ? 'text-sm' : 'text-lg'"
      >
        {{ post.title }}
      </h3>
      <p
        v-if="variant !== 'compact' && post.description"
        class="mt-xs text-sm text-neutral-text-tertiary leading-relaxed line-clamp-2 flex-1 min-h-0"
      >
        {{ post.description }}
      </p>
      <div v-if="post.tags?.length && variant !== 'compact'" class="mt-xs flex flex-wrap gap-1">
        <span
          v-for="t in post.tags.slice(0, 4)"
          :key="t"
          class="text-[10px] px-1.5 py-0.5 rounded-full bg-primary-500/10 text-primary-500"
        >#{{ t }}</span>
      </div>
      <div class="mt-xs pt-xs border-t border-neutral-border-secondary flex items-center justify-between flex-wrap gap-xs">
        <PostMeta :post="post" compact :show-author="variant !== 'compact'" />
        <PostStats :post="post" compact />
      </div>
    </div>
  </NuxtLink>
</template>
