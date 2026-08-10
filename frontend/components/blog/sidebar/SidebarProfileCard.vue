<!--
  SidebarProfileCard — 对应 Astro src/components/blog/sidebar/SidebarProfile.astro
  展示博主头像/昵称/简介 + 统计（文章/分类/标签/评论/运行天数）
  数据接入：阶段 4 时由 useFetch("/api/site/profile") 替换占位
-->
<script setup lang="ts">
interface Props {
  avatar?: string | null;
  nickname?: string;
  bio?: string;
  stats?: { articles?: number; categories?: number; tags?: number; comments?: number; days?: number };
}
withDefaults(defineProps<Props>(), {
  avatar: null,
  nickname: "Choyu Choyeon",
  bio: "一名热爱分享的开发者 · 以代码与文字记录世界",
  stats: () => ({ articles: 64, categories: 12, tags: 233, comments: 1024, days: 365 }),
});
</script>

<template>
  <section
    class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary text-center"
    aria-label="博主资料"
    data-testid="sidebar-profile-card"
  >
    <div class="flex flex-col items-center">
      <div
        class="w-24 h-24 rounded-full ring-4 ring-primary-500/10 shadow-lg overflow-hidden mb-sm bg-gradient-to-br from-primary-300 via-nebula-blue-50 to-rosetta-gold-light flex items-center justify-center"
      >
        <NuxtImg
          v-if="avatar"
          :src="avatar"
          :alt="nickname || '博主头像'"
          loading="lazy"
          class="w-full h-full object-cover"
        />
        <span v-else class="text-2xl font-bold text-white drop-shadow-sm">{{ (nickname || "R").slice(0,1) }}</span>
      </div>
      <h2 class="text-lg font-semibold text-neutral-text-primary">{{ nickname }}</h2>
      <p class="mt-xs text-sm text-neutral-text-tertiary line-clamp-2 max-w-[260px]">{{ bio }}</p>

      <!-- 社交按钮（占位，阶段 3-5 加具体链接） -->
      <div class="mt-md flex items-center gap-2">
        <a href="#" aria-label="GitHub" class="w-8 h-8 rounded-full bg-neutral-fill-hover hover:bg-primary-500 hover:text-white text-neutral-text-secondary transition-all duration-fast flex items-center justify-center">
          <Icon name="mdi:github" class="w-4 h-4" />
        </a>
        <a href="#" aria-label="Email" class="w-8 h-8 rounded-full bg-neutral-fill-hover hover:bg-primary-500 hover:text-white text-neutral-text-secondary transition-all duration-fast flex items-center justify-center">
          <Icon name="material-symbols:mail-outline-rounded" class="w-4 h-4" />
        </a>
        <a href="#" aria-label="RSS" class="w-8 h-8 rounded-full bg-neutral-fill-hover hover:bg-primary-500 hover:text-white text-neutral-text-secondary transition-all duration-fast flex items-center justify-center">
          <Icon name="material-symbols:rss-feed-rounded" class="w-4 h-4" />
        </a>
        <button type="button" aria-label="更多" class="w-8 h-8 rounded-full bg-neutral-fill-hover hover:bg-primary-500 hover:text-white text-neutral-text-secondary transition-all duration-fast flex items-center justify-center">
          <Icon name="material-symbols:add-rounded" class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Stats -->
    <dl class="mt-lg grid grid-cols-5 gap-xs text-center border-t border-neutral-border-secondary pt-lg text-xs text-neutral-text-tertiary">
      <div>
        <dt class="text-neutral-text-quaternary">文章</dt>
        <dd class="mt-0.5 font-semibold text-neutral-text-primary">{{ stats?.articles ?? 0 }}</dd>
      </div>
      <div>
        <dt class="text-neutral-text-quaternary">分类</dt>
        <dd class="mt-0.5 font-semibold text-neutral-text-primary">{{ stats?.categories ?? 0 }}</dd>
      </div>
      <div>
        <dt class="text-neutral-text-quaternary">标签</dt>
        <dd class="mt-0.5 font-semibold text-neutral-text-primary">{{ stats?.tags ?? 0 }}</dd>
      </div>
      <div>
        <dt class="text-neutral-text-quaternary">评论</dt>
        <dd class="mt-0.5 font-semibold text-neutral-text-primary">{{ stats?.comments ?? 0 }}</dd>
      </div>
      <div>
        <dt class="text-neutral-text-quaternary">天数</dt>
        <dd class="mt-0.5 font-semibold text-neutral-text-primary">{{ stats?.days ?? 0 }}</dd>
      </div>
    </dl>
  </section>
</template>
