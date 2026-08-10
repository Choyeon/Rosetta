<script setup lang="ts">
definePageMeta({ layout: "default", middleware: [] });
const route = useRoute();
const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 10;
const keyword = ref(String(route.query.q || ""));
const category = ref(String(route.query.category || ""));
const tag = ref(String(route.query.tag || ""));
watch([() => route.query.page, () => route.query.q, () => route.query.category, () => route.query.tag], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  category.value = String(route.query.category || "");
  tag.value = String(route.query.tag || "");
});

// 双源查询策略（前端 Nuxt Content 优先 → 后端回退）：
// 1) queryContent 查本地 content/posts/**（64 篇种子）
// 2) /api/posts 查后端（真实 DB 数据），后端可用时合并去重
interface Post { id?: number | string; slug: string; title: string; description?: string; image?: string; published?: string; updated?: string; tags?: string[]; category?: string; pinned?: boolean; author?: string; }

const params = computed(() => ({
  page: page.value,
  pageSize,
  keyword: keyword.value || undefined,
  category: category.value || undefined,
  tag: tag.value || undefined,
  excludePassword: true,
  _timeout: 8000,
}));
const { data: apiData, pending } = await useFetch<any>(() => "/api/posts", {
  query: params,
  default: () => ({ items: [], total: 0, page: 1, pageSize, totalPages: 1 }),
  lazy: true,
  server: true,
});
// 本地 Nuxt Content 补充（置顶 + 最近 10 条）
const { data: contentTop } = await useAsyncData("posts-content-top", () =>
  queryContent<Post>("/posts")
    .where({ draft: { $ne: true } })
    .sort({ pinned: -1, published: -1 })
    .limit(5)
    .find()
);

const list = computed<Post[]>(() => (apiData.value?.items?.length ? apiData.value.items : contentTop.value || []));
const total = computed(() => apiData.value?.total ?? contentTop.value?.length ?? 0);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

useHead({
  title: "文章列表 - Rosetta",
  meta: [
    { name: "description", content: "浏览 Rosetta 博客的全部技术文章与随笔。" },
    { property: "og:title", content: "文章列表 - Rosetta" },
  ],
});
</script>

<template>
  <div class="space-y-lg">
    <!-- Header: 搜索 + 分类/标签筛选 -->
    <section class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm p-lg flex flex-col sm:flex-row gap-xs sm:items-center">
      <div class="relative flex-1">
        <Icon name="material-symbols:search-rounded" class="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-text-tertiary" />
        <input
          v-model="keyword"
          type="search"
          placeholder="搜索标题/标签/描述…（回车生效）"
          class="w-full h-10 pl-10 pr-4 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm placeholder:text-neutral-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all"
          @keyup.enter="navigateTo({ path: '/posts', query: { ...route.query, q: keyword || undefined, page: 1 } })"
        />
      </div>
      <div class="flex items-center gap-xs flex-wrap">
        <NuxtLink
          v-for="cat in ['前端开发','后端开发','项目实战','迁移笔记','文章示例']"
          :key="cat"
          :to="{ path: '/posts', query: { category: cat === category ? undefined : cat, page: 1 } }"
          class="px-3 py-1.5 rounded-full text-xs border transition-all duration-fast"
          :class="category === cat ? 'bg-primary-500 text-white border-primary-500' : 'border-neutral-border-secondary text-neutral-text-secondary hover:border-primary-500 hover:text-primary-500'"
        >#{{ cat }}</NuxtLink>
      </div>
    </section>

    <!-- Post list -->
    <section class="space-y-md">
      <div class="flex items-end justify-between">
        <h1 class="text-xl font-bold text-neutral-text-primary">
          全部文章 <span class="text-neutral-text-quaternary font-normal text-sm ml-xs">共 {{ total }} 篇</span>
        </h1>
        <p v-if="pending" class="text-sm text-neutral-text-tertiary animate-pulse">加载中…</p>
      </div>

      <TransitionGroup name="list" tag="div" class="space-y-sm">
        <NuxtLink
          v-for="p in list"
          :key="p.slug"
          :to="`/posts/${p.slug}`"
          class="group block bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-md hover:-translate-y-0.5 hover:shadow-md hover:border-primary-500/30 transition-all duration-fast ease-out"
        >
          <div class="flex items-start gap-md">
            <div
              class="w-28 h-20 shrink-0 rounded-lg bg-gradient-to-br from-primary-500/10 to-rosetta-gold/20 overflow-hidden relative"
            >
              <NuxtImg
                v-if="p.image"
                :src="p.image"
                :alt="p.title"
                format="avif"
                loading="lazy"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-normal ease-out"
              />
              <div v-else class="absolute inset-0 flex items-center justify-center text-primary-500/40">
                <Icon name="material-symbols:article-rounded" class="w-10 h-10" />
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-xs flex-wrap">
                <span v-if="p.pinned" class="px-2 py-0.5 rounded bg-warning-500/15 text-warning-700 text-[10px] font-semibold">置顶</span>
                <span v-if="p.category" class="text-xs text-primary-500 font-medium">#{{ p.category }}</span>
                <span v-for="t in p.tags?.slice?.(0,3)" :key="t" class="text-xs text-neutral-text-tertiary">{{ t }}</span>
              </div>
              <h3 class="mt-xs text-base font-semibold text-neutral-text-primary group-hover:text-primary-500 line-clamp-1">
                {{ p.title }}
              </h3>
              <p class="mt-xs text-sm text-neutral-text-secondary line-clamp-2 leading-relaxed">
                {{ p.description || p.title }}
              </p>
              <p class="mt-xs text-xs text-neutral-text-quaternary flex items-center gap-sm">
                <Icon name="material-symbols:calendar-month-rounded" class="w-3.5 h-3.5" />
                {{ p.published ? new Date(p.published).toLocaleDateString() : "—" }}
                <span v-if="p.author" class="flex items-center gap-xs">
                  <Icon name="material-symbols:person-rounded" class="w-3.5 h-3.5" />{{ p.author }}
                </span>
              </p>
            </div>
          </div>
        </NuxtLink>
        <div
          v-if="!pending && list.length === 0"
          class="text-center py-2xl text-neutral-text-tertiary text-sm"
        >暂无符合条件的文章</div>
      </TransitionGroup>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-between border-t border-neutral-border-secondary pt-md">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/posts', query: { ...route.query, page: page - 1 } }"
          class="px-4 py-2 rounded-md text-sm bg-neutral-fill-hover hover:bg-neutral-fill-active inline-flex items-center gap-xs"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-sm text-neutral-text-tertiary">{{ page }} / {{ totalPages }}</span>
        <NuxtLink
          v-if="page < totalPages"
          :to="{ path: '/posts', query: { ...route.query, page: page + 1 } }"
          class="px-4 py-2 rounded-md text-sm bg-primary-500 text-white hover:bg-primary-400 inline-flex items-center gap-xs"
        >下一页</NuxtLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.list-enter-active, .list-leave-active { transition: all 200ms ease-out; }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateY(6px); }
.list-move { transition: transform 240ms ease; }
</style>
