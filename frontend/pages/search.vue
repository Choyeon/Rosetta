<script setup lang="ts">
definePageMeta({ layout: "default" });
const route = useRoute();
const q = String(route.query.q || "");
const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(q);
useHead({ title: q ? `搜索：${q} - Rosetta` : "搜索 - Rosetta" });

const { data, pending } = await useFetch<any>(() => "/api/posts", {
  query: computed(() => ({ keyword: q, page: page.value, pageSize, _timeout: 10000 })),
  default: () => ({ items: [], total: 0 }),
  lazy: true,
});
// Nuxt Content 全文搜索（local）—— 回退
const { data: local } = await useAsyncData(
  () => "search-local-" + q + "-" + page.value,
  () => q ? queryContent("/posts").where({ draft: { $ne: true } }).search(q).limit(20).find() : Promise.resolve([])
);
const items = computed(() => (data.value?.items?.length ? data.value.items : local.value || []));
</script>

<template>
  <div class="space-y-lg">
    <header class="bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary shadow-sm p-lg">
      <h1 class="text-2xl font-bold text-neutral-text-primary">全站搜索</h1>
      <form class="mt-md flex gap-xs" @submit.prevent="navigateTo({ path: '/search', query: { q: keyword || undefined } })">
        <input
          v-model="keyword"
          type="search"
          placeholder="输入关键字：Vue / Nuxt / FastAPI / 文章示例…"
          class="flex-1 h-11 px-4 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500"
        />
        <button class="h-11 px-5 rounded-lg bg-primary-500 text-white font-medium hover:bg-primary-400 transition-colors inline-flex items-center gap-xs">
          <Icon name="material-symbols:search-rounded" class="w-5 h-5" />搜索
        </button>
      </form>
    </header>

    <section>
      <p class="text-sm text-neutral-text-tertiary mb-xs">
        <template v-if="q">关于 "<strong class="text-neutral-text-primary">{{ q }}</strong>" 共找到 {{ data?.total || items.length }} 个结果。</template>
        <template v-else>输入关键字开始搜索。</template>
        <span v-if="pending" class="animate-pulse ml-xs">加载中…</span>
      </p>
      <TransitionGroup name="list" tag="div" class="space-y-sm">
        <NuxtLink
          v-for="p in items"
          :key="p.slug || p._path"
          :to="`/posts/${p.slug || (p._path||'').replace('/posts/','')}`"
          class="block p-md bg-neutral-bg-container border border-neutral-border-secondary rounded-xl hover:border-primary-500/40 transition-all"
        >
          <h3 class="font-semibold text-neutral-text-primary hover:text-primary-500">{{ p.title }}</h3>
          <p class="mt-xs text-sm text-neutral-text-secondary line-clamp-2">{{ p.description || p.excerpt || p.title }}</p>
        </NuxtLink>
        <p v-if="!pending && items.length === 0 && q" class="text-sm text-neutral-text-tertiary text-center py-xl">没有匹配的结果。</p>
      </TransitionGroup>
    </section>
  </div>
</template>
