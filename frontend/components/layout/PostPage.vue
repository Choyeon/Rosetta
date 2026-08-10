<!--
  PostPage — 文章详情页主体容器（封面 + 元信息 + 正文 + 操作栏）
  slot: header/cover/meta/content/footer/comments
  props: post（Post 类型）
-->
<script setup lang="ts">
import type { Post } from "./PostCard.vue";

interface Props {
  post: Post;
  wordsCount?: number;
  showEdit?: boolean;
  editHref?: string;
}
withDefaults(defineProps<Props>(), { wordsCount: 0, showEdit: true, editHref: "" });

const runtimeConfig = useRuntimeConfig();
const siteUrl = computed(() => (runtimeConfig.public as any)?.siteUrl || window.location.origin);
const shareUrl = computed(() => `${siteUrl.value}${props.post._path}`);

const liked = ref(false);
const bookmarked = ref(false);

async function copyLink() {
  try {
    await navigator.clipboard.writeText(shareUrl.value);
    // 简单的无依赖提示
    const tip = document.createElement("div");
    tip.className = "fixed top-20 left-1/2 -translate-x-1/2 z-[9999] px-3 py-1.5 rounded-full bg-neutral-text-primary text-white text-xs shadow-lg";
    tip.textContent = "链接已复制到剪贴板";
    document.body.appendChild(tip);
    setTimeout(() => tip.remove(), 1600);
  } catch { /* ignore */ }
}
</script>

<template>
  <article class="post-page space-y-md">
    <!-- 封面 Hero -->
    <div v-if="post.image" class="relative rounded-2xl overflow-hidden border border-neutral-border-secondary shadow-sm aspect-[21/9] bg-neutral-fill-hover">
      <NuxtImg
        :src="post.image"
        :alt="post.title"
        class="w-full h-full object-cover"
        priority
      />
      <div class="absolute inset-0 bg-gradient-to-t from-neutral-bg-container/95 via-neutral-bg-container/20 to-transparent" />
    </div>

    <!-- 标题区 -->
    <header class="bg-neutral-bg-container rounded-2xl p-lg border border-neutral-border-secondary shadow-sm space-y-md">
      <div>
        <CategoryBar
          :category="post.category"
          :title="post.title"
          :tags="post.tags"
        />
      </div>
      <div class="flex flex-wrap items-center justify-between gap-md">
        <PostMeta :post="post" />
        <div class="flex items-center gap-xs flex-wrap">
          <PostStats :post="post" :show-words="wordsCount > 0" :words-count="wordsCount" />
          <a
            v-if="showEdit && editHref"
            :href="editHref"
            target="_blank"
            rel="noopener nofollow"
            class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs text-neutral-text-tertiary hover:text-primary-500 hover:bg-neutral-fill-hover transition-colors"
          >
            <Icon name="material-symbols:edit-rounded" class="w-3.5 h-3.5" />
            编辑
          </a>
        </div>
      </div>
    </header>

    <!-- 正文区域 -->
    <section class="bg-neutral-bg-container rounded-2xl p-lg sm:p-xl border border-neutral-border-secondary shadow-sm">
      <slot name="content" />
    </section>

    <!-- 操作栏 -->
    <section class="bg-neutral-bg-container rounded-2xl p-md border border-neutral-border-secondary shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-sm">
        <div class="flex items-center gap-1">
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all text-sm"
            :class="liked ? 'bg-rose-500 text-white shadow-sm' : 'text-rose-500 hover:bg-rose-500/10 border border-rose-500/20'"
            :aria-pressed="liked"
            @click="liked = !liked"
          >
            <Icon :name="liked ? 'material-symbols:favorite-rounded' : 'material-symbols:favorite-outline-rounded'" class="w-4 h-4" />
            <span class="font-medium">{{ (post.likes || 0) + (liked ? 1 : 0) }}</span>
            <span class="hidden sm:inline">点赞</span>
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all text-sm"
            :class="bookmarked ? 'bg-amber-500 text-white shadow-sm' : 'text-amber-500 hover:bg-amber-500/10 border border-amber-500/20'"
            :aria-pressed="bookmarked"
            @click="bookmarked = !bookmarked"
          >
            <Icon :name="bookmarked ? 'material-symbols:bookmark-rounded' : 'material-symbols:bookmark-outline-rounded'" class="w-4 h-4" />
            <span class="hidden sm:inline">收藏</span>
          </button>
        </div>
        <div class="flex items-center gap-1">
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-neutral-text-secondary hover:text-primary-500 hover:bg-primary-500/10 border border-transparent hover:border-primary-500/20 transition-all"
            @click="copyLink"
          >
            <Icon name="material-symbols:link-rounded" class="w-4 h-4" />
            <span class="hidden sm:inline">复制链接</span>
          </button>
          <DropdownMenu
            :items="[
              { key: 'twitter', label: '分享到 Twitter/X', icon: 'simple-icons:x', href: `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(post.title)}` },
              { key: 'telegram', label: '分享到 Telegram', icon: 'simple-icons:telegram', href: `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(post.title)}` },
              { key: 'weibo', label: '分享到微博', icon: 'simple-icons:sinaweibo', href: `https://service.weibo.com/share/share.php?url=${encodeURIComponent(shareUrl)}&title=${encodeURIComponent(post.title)}` },
              { key: 'email', label: '邮件分享', icon: 'material-symbols:mail-outline-rounded', href: `mailto:?subject=${encodeURIComponent(post.title)}&body=${encodeURIComponent(shareUrl)}` },
              { key: 'd1', label: '', divider: true },
              { key: 'report', label: '举报/反馈', icon: 'material-symbols:flag-rounded', danger: true },
            ]"
          >
            <template #default="{ toggle }">
              <button
                type="button"
                class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-neutral-text-secondary hover:text-primary-500 hover:bg-primary-500/10 border border-transparent hover:border-primary-500/20 transition-all"
                @click="toggle()"
              >
                <Icon name="material-symbols:share-rounded" class="w-4 h-4" />
                分享
              </button>
            </template>
          </DropdownMenu>
        </div>
      </div>
    </section>

    <!-- 推荐 + 评论 -->
    <slot name="footer" />
  </article>
</template>

<style scoped>
.post-page :deep(.prose) {
  max-width: none;
  color: var(--rosetta-text-primary, rgba(0,0,0,0.88));
  font-size: calc(1rem * var(--read-font-scale, 1));
  line-height: calc(1.75 * var(--read-line-scale, 1));
}
.post-page :deep(.prose p) {
  margin-top: calc(1rem * var(--read-gap, 1));
  margin-bottom: calc(1rem * var(--read-gap, 1));
}
</style>
