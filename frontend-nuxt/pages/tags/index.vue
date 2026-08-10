<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "标签 - Rosetta", meta: [{ name: "description", content: "全部标签：浏览 Rosetta 博客的分类话题。" }] });

// 本地 content: 从所有 post.tags 聚合计数 → /api/tags 后端聚合回退
const { data: contentTags } = await useAsyncData<{ name: string; count: number }[]>("tags-agg", async () => {
  try {
    const posts = await queryContent<{ tags?: string[] }>("/posts").where({ draft: { $ne: true } }).only(["tags"]).find();
    const map = new Map<string, number>();
    posts.forEach(p => (p.tags || []).forEach(t => map.set(t, (map.get(t) || 0) + 1)));
    return [...map.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);
  } catch { return []; }
});
const { data: apiTags } = await useFetch<any[]>("/api/tags", { lazy: true, server: true, default: () => [] });
const list = computed(() => (apiTags.value && apiTags.value.length ? apiTags.value as any[] : contentTags.value || []));
</script>

<template>
  <div class="space-y-lg">
    <header>
      <h1 class="text-3xl font-bold text-neutral-text-primary">所有标签</h1>
      <p class="mt-xs text-sm text-neutral-text-tertiary">共 {{ list.length }} 个标签，点击进入对应文章列表。</p>
    </header>
    <SidebarTagCloudCard :tags="list.map((x, i) => ({ id: i, name: x.name, count: x.count, slug: encodeURIComponent(x.name) }))" title="标签云" :limit="999" class="!p-0 !border-0 !shadow-none !rounded-none" />
  </div>
</template>
