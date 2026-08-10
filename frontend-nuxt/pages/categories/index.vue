<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "分类 - Rosetta" });

// 聚合：content 层按 category 计数 / 后端回退
const { data: local } = await useAsyncData("cats-agg", async () => {
  const posts = await queryContent<{ category?: string }>("/posts").where({ draft: { $ne: true } }).only(["category"]).find();
  const m = new Map<string, number>();
  posts.forEach(p => { const k = p.category || "未分类"; m.set(k, (m.get(k) || 0) + 1); });
  return [...m.entries()].map(([name, count]) => ({ slug: encodeURIComponent(name), name, count })).sort((a, b) => b.count - a.count);
});
const { data: api } = await useFetch<any[]>("/api/categories", { default: () => [], lazy: true });
const list = computed(() => (api.value && api.value.length ? api.value : local.value || []));
</script>

<template>
  <div class="space-y-lg">
    <header>
      <h1 class="text-3xl font-bold text-neutral-text-primary">全部分类</h1>
      <p class="mt-xs text-sm text-neutral-text-tertiary">共 {{ list.length }} 个分类。</p>
    </header>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-md">
      <NuxtLink
        v-for="c in list"
        :key="c.name"
        :to="`/categories/${c.slug || encodeURIComponent(c.name)}`"
        class="group relative bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-lg hover:shadow-md hover:border-primary-500/40 hover:-translate-y-0.5 transition-all"
      >
        <div class="absolute top-0 left-0 w-full h-1 rounded-t-xl bg-gradient-to-r from-primary-500 via-nebula-blue to-rosetta-gold opacity-0 group-hover:opacity-100 transition-opacity" />
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-neutral-text-primary group-hover:text-primary-500 transition-colors">{{ c.name }}</h2>
          <span class="px-2 py-0.5 rounded-full bg-neutral-fill-hover text-xs text-neutral-text-tertiary">{{ c.count }} 篇</span>
        </div>
        <p class="mt-xs text-xs text-neutral-text-quaternary">点击查看全部文章 →</p>
      </NuxtLink>
    </div>
  </div>
</template>
