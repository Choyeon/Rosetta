<script setup lang="ts">
definePageMeta({ layout: "default" });
const route = useRoute();
const tag = computed(() => decodeURIComponent(String(route.params.slug || "")));
useHead({ title: `标签：${tag.value} - Rosetta` });
const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 10;
const { data } = await useFetch<any>(() => "/api/posts", {
  query: computed(() => ({ tag: tag.value, page: page.value, pageSize, _timeout: 8000 })),
  default: () => ({ items: [], total: 0 }),
  lazy: true,
});
// 本地补充
const { data: local } = await useAsyncData(() => "tag-" + tag.value, () =>
  queryContent("/posts").where({ draft: { $ne: true }, tags: { $contains: tag.value } }).sort({ published: -1 }).limit(20).find()
);
const items = computed(() => (data.value?.items?.length ? data.value.items : local.value || []));
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-baseline gap-xs">
      <h1 class="text-2xl font-bold text-neutral-text-primary">标签</h1>
      <span class="px-3 py-1 rounded-full bg-primary-500 text-white text-sm font-medium">#{{ tag }}</span>
      <span class="text-sm text-neutral-text-tertiary">共 {{ data?.total || items.length }} 篇</span>
    </header>
    <div class="space-y-sm">
      <NuxtLink
        v-for="p in items"
        :key="p.slug || p._path"
        :to="`/posts/${p.slug || (p._path||'').replace('/posts/','')}`"
        class="block p-md bg-neutral-bg-container border border-neutral-border-secondary rounded-xl hover:border-primary-500/40 hover:shadow-sm transition-all"
      >
        <h3 class="font-semibold text-neutral-text-primary hover:text-primary-500">{{ p.title }}</h3>
        <p class="mt-xs text-sm text-neutral-text-secondary line-clamp-1">{{ p.description || p.excerpt }}</p>
        <p class="mt-xs text-xs text-neutral-text-quaternary">{{ p.published ? new Date(p.published).toLocaleDateString() : '' }}</p>
      </NuxtLink>
      <p v-if="items.length === 0" class="text-sm text-neutral-text-tertiary text-center py-xl">还没有相关文章。</p>
    </div>
  </div>
</template>
