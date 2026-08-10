<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({
  title: "Rosetta — 以内容与体验为核心的现代化博客引擎",
  meta: [
    { name: "description", content: "Rosetta：Nuxt 4 + FastAPI 驱动的现代化博客系统。支持 Markdown、分类/标签、多语言、站内搜索、评论、媒体管理与 SEO。" },
    { property: "og:title", content: "Rosetta — 现代化博客引擎" },
    { property: "og:description", content: "以内容与体验为核心的现代化博客引擎。" },
    { property: "og:type", content: "website" },
  ],
});

// 置顶 + 最近文章：API → 本地 content 回退
interface Post { slug: string; title: string; description?: string; image?: string; published?: string; category?: string; tags?: string[]; pinned?: boolean }
const { data: feed } = await useFetch<any>("/api/posts", {
  query: { pinnedFirst: true, pageSize: 10, _timeout: 8000 },
  default: () => ({ items: [] }),
  lazy: true,
  server: true,
});
const { data: local } = await useAsyncData("home-posts", () =>
  queryContent<Post>("/posts").where({ draft: { $ne: true } }).sort({ pinned: -1, published: -1 }).limit(10).find()
);
const posts = computed<Post[]>(() => (feed.value?.items?.length ? feed.value.items : local.value || []));
const pinned = computed(() => posts.value.filter(p => p.pinned).slice(0, 2));
const recent = computed(() => posts.value.slice(0, 8));

const categories = ["前端开发", "后端开发", "项目实战", "迁移笔记", "文章示例"];
</script>

<template>
  <div class="space-y-2xl">
    <!-- Hero -->
    <section class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary-500 via-nebula-blue-75/80 to-rosetta-gold-dark shadow-lg p-2xl md:p-3xl text-white">
      <div class="pointer-events-none absolute inset-0 opacity-20" aria-hidden style="background-image: radial-gradient(circle at 20% 20%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 80%, #fff 1px, transparent 1px); background-size: 24px 24px;"/>
      <div class="relative max-w-3xl">
        <p class="text-sm font-medium uppercase tracking-[0.24em] text-white/80 mb-sm">Rosetta · Lightweight Blog System</p>
        <h1 class="text-[clamp(2rem,4vw,3rem)] font-bold leading-[1.15] mb-md">
          以<span class="text-rosetta-gold">内容</span>与<span class="text-rosetta-gold">体验</span>为核心的
          <br class="hidden md:block"/>现代化博客引擎
        </h1>
        <p class="text-white/90 max-w-2xl leading-relaxed text-[15px]">
          前端已全面迁移至 <strong>Nuxt 4 + Vue 3 + Tailwind v4</strong>，配合
          <strong>FastAPI + PostgreSQL</strong> 后端，提供 SSR、增量静态生成、
          结构化 SEO、标签 / 分类 / 归档、全文搜索、Markdown 编辑器和媒体管理等能力。
        </p>
        <div class="mt-xl flex flex-wrap gap-xs">
          <NuxtLink to="/posts" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-white text-primary-700 font-semibold shadow-sm hover:bg-neutral-bg-spot active:translate-y-px transition-all duration-fast">
            <Icon name="material-symbols:menu-book-rounded" class="w-5 h-5"/>浏览文章
          </NuxtLink>
          <NuxtLink to="/archive" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-white/10 backdrop-blur-sm hover:bg-white/15 text-white font-medium border border-white/20 transition-all">
            <Icon name="material-symbols:calendar-month-rounded" class="w-5 h-5"/>时间归档
          </NuxtLink>
          <NuxtLink to="/about" class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-rosetta-gold text-neutral-text-primary font-semibold shadow-sm hover:bg-rosetta-gold-dark hover:text-white transition-all">
            <Icon name="material-symbols:info-rounded" class="w-5 h-5"/>关于项目
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- Category strip -->
    <section class="flex flex-wrap gap-xs" aria-label="分类导航">
      <NuxtLink v-for="c in categories" :key="c"
        :to="{ path: '/categories', query: undefined }"
        @click="navigateTo(`/categories/${encodeURIComponent(c)}`)"
        class="group inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-neutral-border-secondary bg-neutral-bg-container text-sm text-neutral-text-secondary hover:text-primary-500 hover:border-primary-500/40 hover:shadow-sm transition-all"
      >
        <span class="w-2 h-2 rounded-full bg-gradient-to-r from-primary-500 to-rosetta-gold opacity-70 group-hover:opacity-100"/>
        {{ c }}
      </NuxtLink>
    </section>

    <!-- Pinned -->
    <section v-if="pinned.length" class="space-y-sm">
      <div class="flex items-end justify-between">
        <h2 class="text-xl font-bold text-neutral-text-primary inline-flex items-center gap-xs">
          <Icon name="material-symbols:push-pin-rounded" class="w-5 h-5 text-warning-500"/>置顶推荐
        </h2>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
        <NuxtLink
          v-for="p in pinned"
          :key="p.slug"
          :to="`/posts/${p.slug}`"
          class="group relative rounded-2xl overflow-hidden bg-neutral-bg-container border border-warning-500/30 hover:border-primary-500/40 hover:shadow-md transition-all"
        >
          <div class="h-40 md:h-48 bg-gradient-to-br from-primary-500/20 via-nebula-blue/10 to-rosetta-gold/20 relative overflow-hidden">
            <NuxtImg v-if="p.image" :src="p.image" :alt="p.title" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-normal" format="avif" loading="lazy"/>
            <div v-else class="absolute inset-0 flex items-center justify-center text-primary-500/40"><Icon name="material-symbols:article-rounded" class="w-16 h-16"/></div>
            <span class="absolute top-xs left-xs px-2 py-0.5 rounded bg-warning-500/90 text-white text-[10px] font-bold shadow-xs">PIN</span>
          </div>
          <div class="p-md">
            <div class="flex items-center gap-xs text-xs text-neutral-text-tertiary">
              <span v-if="p.category" class="text-primary-500 font-medium">#{{ p.category }}</span>
              <span>·</span><Icon name="material-symbols:calendar-month-rounded" class="w-3.5 h-3.5"/>
              {{ p.published ? new Date(p.published).toLocaleDateString() : '—' }}
            </div>
            <h3 class="mt-xs text-lg font-semibold text-neutral-text-primary group-hover:text-primary-500 line-clamp-2">{{ p.title }}</h3>
            <p class="mt-xs text-sm text-neutral-text-secondary line-clamp-2 leading-relaxed">{{ p.description }}</p>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- Recent articles -->
    <section class="space-y-md">
      <div class="flex items-end justify-between">
        <h2 class="text-xl font-bold text-neutral-text-primary inline-flex items-center gap-xs">
          <Icon name="material-symbols:bolt-rounded" class="w-5 h-5 text-primary-500"/>最新文章
        </h2>
        <NuxtLink to="/posts" class="text-sm text-primary-500 hover:text-primary-400 inline-flex items-center gap-0.5">
          查看全部 <Icon name="material-symbols:chevron-right-rounded" class="w-4 h-4"/>
        </NuxtLink>
      </div>
      <div class="space-y-sm">
        <NuxtLink
          v-for="p in recent"
          :key="p.slug"
          :to="`/posts/${p.slug}`"
          class="group flex items-start gap-md p-md bg-neutral-bg-container border border-neutral-border-secondary rounded-xl hover:-translate-y-0.5 hover:shadow-md hover:border-primary-500/30 transition-all duration-fast ease-out"
        >
          <div class="w-28 h-20 shrink-0 rounded-lg bg-gradient-to-br from-primary-500/10 to-rosetta-gold/20 overflow-hidden relative">
            <NuxtImg v-if="p.image" :src="p.image" :alt="p.title" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-normal" format="avif" loading="lazy"/>
            <div v-else class="absolute inset-0 flex items-center justify-center text-primary-500/40"><Icon name="material-symbols:article-rounded" class="w-10 h-10"/></div>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-xs flex-wrap text-xs">
              <span v-if="p.category" class="text-primary-500 font-medium">#{{ p.category }}</span>
              <span v-for="t in p.tags?.slice?.(0,2)" :key="t" class="text-neutral-text-tertiary">{{ t }}</span>
            </div>
            <h3 class="mt-xs text-base font-semibold text-neutral-text-primary group-hover:text-primary-500 line-clamp-1">{{ p.title }}</h3>
            <p class="mt-xs text-sm text-neutral-text-secondary line-clamp-2 leading-relaxed">{{ p.description }}</p>
            <p class="mt-xs text-xs text-neutral-text-quaternary">{{ p.published ? new Date(p.published).toLocaleDateString() : '' }}</p>
          </div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>
